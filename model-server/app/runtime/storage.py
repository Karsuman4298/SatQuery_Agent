"""Metadata and immutable object adapters. Pixels never enter SQL or vector payloads."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, select, and_, text
from sqlalchemy.exc import IntegrityError


class ObjectStore:
    def __init__(self, root: str, endpoint: str = '', bucket: str = 'satquery', access_key: str = '', secret_key: str = ''):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.bucket = bucket
        self.client = None
        if endpoint:
            import boto3
            from botocore.config import Config
            self.client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=access_key,
                                       aws_secret_access_key=secret_key,
                                       config=Config(connect_timeout=5, read_timeout=20, retries={'max_attempts': 2}))

    def _key(self, key):
        path = PurePosixPath(key)
        if path.is_absolute() or '..' in path.parts or '\\' in key or not key:
            raise ValueError('Invalid object key')
        return str(path)

    def put(self, data: bytes, prefix: str, suffix: str) -> str:
        # Content-addressed objects are immutable and safe to retry.
        key = self._key(f'{prefix}/{hashlib.sha256(data).hexdigest()}.{suffix}')
        if self.client:
            from botocore.exceptions import ClientError
            try:
                self.client.head_bucket(Bucket=self.bucket)
            except ClientError as exc:
                if exc.response['Error']['Code'] not in {'404', 'NoSuchBucket'}:
                    raise
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                except ClientError as created:
                    if created.response['Error']['Code'] != 'BucketAlreadyOwnedByYou': raise
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        else:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                temporary = path.with_name(path.name + f'.{uuid4()}.tmp')
                temporary.write_bytes(data)
                temporary.replace(path)
        return key

    def get(self, key: str) -> bytes:
        key = self._key(key)
        if self.client:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Object escapes configured storage')
        return path.read_bytes()


class MetadataStore:
    """Portable local test profile; PostgreSQL/PostGIS in the deployment profile."""
    def __init__(self, url: str):
        self.engine = create_engine(url, pool_pre_ping=True)
        metadata = MetaData()
        self.records = Table('satquery_records', metadata,
            Column('owner', String(128), primary_key=True), Column('kind', String(32), primary_key=True),
            Column('id', String(64), primary_key=True), Column('thread_id', String(64), index=True),
            Column('data', Text, nullable=False), Column('created_at', String(64), nullable=False, index=True))
        metadata.create_all(self.engine)
        self.postgis = self.engine.dialect.name == 'postgresql'
        if self.postgis:
            with self.engine.begin() as db:
                db.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
                db.execute(text('CREATE TABLE IF NOT EXISTS satquery_footprints (owner TEXT NOT NULL, asset_id TEXT NOT NULL, footprint geometry(Polygon,4326), PRIMARY KEY(owner,asset_id))'))
                db.execute(text('CREATE INDEX IF NOT EXISTS satquery_footprints_gix ON satquery_footprints USING GIST(footprint)'))

    def put(self, owner: str, kind: str, key: str, data: dict, thread_id: str | None = None):
        condition = and_(self.records.c.owner == owner, self.records.c.kind == kind, self.records.c.id == str(key))
        values = {'owner': owner, 'kind': kind, 'id': str(key), 'thread_id': thread_id,
                  'data': json.dumps(data, default=str, allow_nan=False),
                  'created_at': str(data.get('started_at') or data.get('timestamp') or data.get('created_at') or datetime.now(timezone.utc).isoformat())}
        try:
            with self.engine.begin() as db:
                if not db.execute(self.records.update().where(condition).values(**values)).rowcount:
                    db.execute(self.records.insert().values(**values))
        except IntegrityError:
            with self.engine.begin() as db:
                db.execute(self.records.update().where(condition).values(**values))
        if kind == 'asset' and self.postgis and data.get('bbox_geo'):
            left, bottom, right, top = data['bbox_geo']
            with self.engine.begin() as db:
                db.execute(text('INSERT INTO satquery_footprints VALUES (:owner,:id,ST_MakeEnvelope(:l,:b,:r,:t,4326)) ON CONFLICT(owner,asset_id) DO UPDATE SET footprint=EXCLUDED.footprint'),
                           dict(owner=owner, id=str(key), l=left, b=bottom, r=right, t=top))

    def get(self, owner: str, kind: str, key: str):
        with self.engine.connect() as db:
            value = db.execute(select(self.records.c.data).where(self.records.c.owner == owner,
                self.records.c.kind == kind, self.records.c.id == str(key))).scalar_one_or_none()
        if value is None:
            raise KeyError('Record not found in this scope')
        return json.loads(value)

    def list(self, owner: str, kind: str, thread_id: str | None = None, limit: int = 100):
        query = select(self.records.c.data).where(self.records.c.owner == owner, self.records.c.kind == kind)
        if thread_id:
            query = query.where(self.records.c.thread_id == thread_id)
        with self.engine.connect() as db:
            return [json.loads(value) for value in db.execute(query.order_by(self.records.c.created_at.desc(), self.records.c.id.desc()).limit(limit)).scalars()]

    def overlapping(self, owner: str, bbox: list[float]):
        if self.postgis:
            with self.engine.connect() as db:
                return list(db.execute(text('SELECT asset_id FROM satquery_footprints WHERE owner=:owner AND ST_Intersects(footprint,ST_MakeEnvelope(:l,:b,:r,:t,4326))'),
                            dict(owner=owner, l=bbox[0], b=bbox[1], r=bbox[2], t=bbox[3])).scalars())
        return [row['asset_id'] for row in self.list(owner, 'asset', limit=10000) if row.get('bbox_geo')
                and row['bbox_geo'][0] <= bbox[2] and row['bbox_geo'][2] >= bbox[0]
                and row['bbox_geo'][1] <= bbox[3] and row['bbox_geo'][3] >= bbox[1]]
