"""Scoped lexical + Qdrant retrieval. Vector payloads contain references, never pixels."""
from __future__ import annotations
import math
import re
from collections import Counter
from uuid import uuid5, NAMESPACE_URL
import httpx


def lexical_rank(query: str, records: list[dict], limit=10):
    terms = re.findall(r'\w+', query.lower())
    documents = [Counter(re.findall(r'\w+', row.get('text', '').lower())) for row in records]
    average = sum(sum(doc.values()) for doc in documents) / max(1, len(documents))
    ranked = []
    for row, document in zip(records, documents):
        score = 0.
        for term in set(terms):
            count = document[term]
            frequency = sum(term in doc for doc in documents)
            idf = math.log(1 + (len(documents) - frequency + .5) / (frequency + .5))
            score += idf * count * 2.2 / (count + 1.2 * (.25 + .75 * sum(document.values()) / max(1., average)))
        if score > 0: ranked.append((row, score))
    return [row for row, _ in sorted(ranked, key=lambda item: item[1], reverse=True)[:limit]]


def rrf(*rankings, limit=5):
    scores, records = {}, {}
    for ranking in rankings:
        for position, row in enumerate(ranking, 1):
            key = row['evidence_id']
            records[key] = row
            scores[key] = scores.get(key, 0.) + 1 / (60 + position)
    return [records[key] for key in sorted(scores, key=scores.get, reverse=True)[:limit]]


class Retrieval:
    def __init__(self, records, qdrant_url='', embedding_url='', embedding_model='nomic-embed-text'):
        self.records = records
        self.qdrant_url = qdrant_url.rstrip('/')
        self.embedding_url = embedding_url.rstrip('/')
        self.embedding_model = embedding_model
        self.collection = 'satquery_evidence_' + re.sub(r'[^a-zA-Z0-9_]', '_', embedding_model)

    async def embed(self, text):
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f'{self.embedding_url}/api/embeddings', json={'model': self.embedding_model, 'prompt': text})
            response.raise_for_status()
            vector = response.json().get('embedding')
            if not vector or not all(math.isfinite(value) for value in vector): raise ValueError('Invalid embedding')
            return vector

    async def index(self, owner, thread_id, evidence, promoted=False, domain="conversation"):
        row = {**evidence.model_dump(mode='json'), 'owner': owner, 'thread_id': str(thread_id), 'promoted': promoted, 'domain': domain}
        self.records.put(owner, 'tile_evidence' if domain == 'asset' else 'evidence', str(evidence.evidence_id), row, str(thread_id))
        if promoted:
            self.records.put(owner, 'memory', str(evidence.evidence_id), row, str(thread_id))
        if not self.qdrant_url: return
        vector = await self.embed(evidence.text)
        async with httpx.AsyncClient(timeout=10) as client:
            collection = await client.get(f'{self.qdrant_url}/collections/{self.collection}')
            if collection.status_code == 404:
                created = await client.put(f'{self.qdrant_url}/collections/{self.collection}', json={'vectors': {'size': len(vector), 'distance': 'Cosine'}})
                # Concurrent workers may create the same collection.
                if created.status_code not in (200, 201, 409): created.raise_for_status()
            else: collection.raise_for_status()
            point = {'id': str(uuid5(NAMESPACE_URL, owner + str(evidence.evidence_id))), 'vector': vector, 'payload': row}
            response = await client.put(f'{self.qdrant_url}/collections/{self.collection}/points?wait=true', json={'points': [point]})
            response.raise_for_status()

    async def search(self, owner, thread_id, asset_ids, query):
        ids = {str(key) for key in asset_ids}
        # SQL owner/thread filtering runs before lexical scoring.
        scoped = self.records.list(owner, 'evidence', str(thread_id), limit=500)
        scoped += self.records.list(owner, 'memory', limit=500)
        scoped += self.records.list(owner, 'tile_evidence', limit=500)
        rows = {row['evidence_id']: row for row in scoped if str(row['asset_id']) in ids}
        lexical = lexical_rank(query, list(rows.values()))
        dense, warnings = [], []
        if self.qdrant_url:
            try:
                vector = await self.embed(query)
                where = {'must': [{'key': 'owner', 'match': {'value': owner}},
                                  {'key': 'asset_id', 'match': {'any': sorted(ids)}}],
                         'should': [{'key': 'thread_id', 'match': {'value': str(thread_id)}},
                                    {'key': 'promoted', 'match': {'value': True}},
                                    {'key': 'domain', 'match': {'value': 'asset'}}]}
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(f'{self.qdrant_url}/collections/{self.collection}/points/query',
                        json={'query': vector, 'filter': where, 'limit': 10, 'with_payload': True})
                    if response.status_code != 404:
                        response.raise_for_status()
                        # Recheck scope after retrieval, including stale vector payloads.
                        dense = [rows[point['payload']['evidence_id']] for point in response.json()['result']['points']
                                 if point['payload'].get('evidence_id') in rows]
            except (httpx.HTTPError, ValueError, KeyError):
                warnings.append('Semantic retrieval unavailable; used scoped lexical retrieval.')
        return rrf(lexical, dense), warnings
