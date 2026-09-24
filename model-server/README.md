# SatQuery model server

This directory implements the model/agent/storage work from `satquery_architecture.pdf`. The original frontend, backend, and root deployment files have been restored and are not changed by this implementation.

## Architecture

The new **asset-reference runtime** is under `app/runtime/`:

| Module | Responsibility |
|---|---|
| `contracts.py` | Typed Asset, QueryPlan, Evidence, Execution, and observable Trace contracts |
| `ingestion.py` | Format/content validation, metadata, SHA-256 identity, original raster preservation, bounded previews, 1024px tiles |
| `storage.py` | Immutable object keys; filesystem/S3 adapters; SQL metadata; PostgreSQL/PostGIS footprints and intersection queries |
| `policies.py` | Allowlisted capabilities, automatic input-aware task routing, pair/date/modality/grid checks |
| `retrieval.py` | Owner/thread/asset filters, BM25-style lexical ranking, optional Qdrant dense retrieval, reciprocal-rank fusion |
| `specialists.py` | VQA, captions, temporal descriptions, optical–SAR joint interpretation, MobileSAM grounding; universal evidence |
| `engine.py` | Reference-only LangGraph: plan → retrieve → execute → verify → finalize; at most two retries |
| `worker.py` | Optional Celery ingestion and caption-derived tile indexing, broker messages containing references only |
| `api.py` | Versioned asset/query/history/mask/job endpoints with scope enforcement |

Raw imagery and masks stay in the object store. SQL holds metadata, conversation records, evidence metadata, jobs, and execution snapshots. Qdrant receives text vectors and reference payloads, not image bytes. Geographic footprints are stored in PostGIS in the PostgreSQL profile. The local SQLite profile supports bounding-box intersection in Python for development.

The working graph state contains asset IDs, typed plans/evidence, bounded text context, and execution records. Specialist adapters resolve preview bytes temporarily at the tool boundary. Large originals never enter the graph or model prompt.

## Local development

Use Python 3.11+, install the requirements, and run from this directory:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5vl:7b
ollama pull nomic-embed-text
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

No paid API is required. Ollama must be running; the downloaded model needs sufficient RAM/VRAM. This is a generic development baseline until an adapted checkpoint is trained and evaluated.

Default storage is `satquery-runtime.db` plus `runtime-objects/`. Local mode has a single fixed owner, `local`; supplying another owner is rejected. These stores are durable across restarts. The `/health` endpoint reports process liveness; `/readiness` checks the configured model's availability.

The existing `/agent` and `/agent/query` base64 interfaces remain available for the original frontend. Their old payload/response format is preserved. They are compatibility paths, not the new reference-only graph. To use the new architecture, call `/v2/query` or supply `asset_ids` to `/agent`; a gateway can make that migration without frontend redesign. Base64-only calls do not gain the v2 raster registry and persisted reference-graph features automatically.

## API workflow

1. Upload a raster through `POST /v2/assets` (multipart: `file`, `modality`, optional `sensor`, `acquisition_time`, `benchmark`). TIFF/GeoTIFF is preferred. PNG/JPEG requires declaring VRSBench, RSVQA, CDVQA, or BigEarthNet.txt provenance.
2. Use the returned `asset_id` in a query:

```json
{
  "thread_id": "00000000-0000-4000-8000-000000000001",
  "query": "Describe the land cover and major objects.",
  "asset_ids": ["<asset UUID>"],
  "task": "auto",
  "max_retries": 1,
  "alignment_confirmed": false,
  "promote_memory": false
}
```

3. `POST /v2/query` returns an execution ID, typed plan, individually cited evidence, limitations, and observable tool trace. Free-form internal reasoning is not returned or stored by the new runtime.
4. `GET /v2/executions/{id}` restores the result; `GET /v2/threads/{id}/executions` lists up to 50 executions. `GET /v2/executions/{id}/masks/{evidence_id}` serves an authorized mask. The execution JSON is the downloadable report.
5. With a broker and worker configured, `POST /v2/ingestions` queues ingestion and returns a job ID. Poll `GET /v2/jobs/{id}`. `POST /v2/assets/{id}/index` queues tile captioning and optional semantic indexing.

For temporal analysis, provide two distinct images in chronological order, acquisition dates, matching modalities, CRS, dimensions and pixel grids. Fusion requires optical/multispectral first and SAR second. Non-georeferenced benchmark pairs require explicit alignment confirmation. Grid matching does not establish subpixel registration.

Scene previews read only the first three bands (or expand one/two bands), with a percentile stretch for non-byte rasters. This is a display representation, not calibrated multispectral or SAR processing. Original data, band names, geotransform, native resolution, and WGS84 footprint remain available in the asset record.

## Optional self-hosted stores

`deploy/compose.yml` adds PostgreSQL/PostGIS, MinIO, Qdrant, Valkey, and a Celery worker without changing the root app deployment. Set these environment variables in your shell or a local Compose env file (do not commit actual credentials):

```sh
export MODEL_DB_PASSWORD='<URL-safe database password>'
export MODEL_S3_USER='<object-store account>'
export MODEL_S3_PASSWORD='<object-store password>'
export MODEL_GATEWAY_KEY='<random service key>'
docker compose -f deploy/compose.yml up --build
```

The object adapter creates its configured bucket on first write if needed. The MinIO console is at localhost:9001. Review/pin image digests for your deployment. The Docker daemon and this full infrastructure profile have not been run in the current environment.

Configure `RUNTIME_DATABASE_URL`, `RUNTIME_S3_ENDPOINT`, `RUNTIME_S3_BUCKET`, `RUNTIME_S3_ACCESS_KEY`, `RUNTIME_S3_SECRET_KEY`, `RUNTIME_QDRANT_URL`, and `RUNTIME_QUEUE_URL` for external self-hosted services. With `RUNTIME_GATEWAY_KEY` configured, requests to the new API and `/agent` must include `X-Satquery-Key` and `X-Satquery-Owner`. Only a trusted backend that has authenticated its user should assert that owner. The service key is not end-user authentication. Legacy specialist/debug routes are internal-only and must not be exposed as a public gateway.

Conversation context is bounded to eight messages; retrieval returns five candidates. Conversation evidence is scoped to its thread and current assets. Long-term promotion is explicit (`promote_memory=true`), limited to completed executions, and still stores model claims as unverified. Tile evidence is owner/asset scoped and reusable across that owner's threads. Retrieved model claims are context, not independent confirmation.

## Training for Colab/Kaggle

`finetune/colab_kaggle.ipynb` and `finetune/train_rs.py` provide a QLoRA workflow for a curated remote-sensing training subset. Use a free GPU runtime and retain checkpoint artifacts before the session expires. The script checks scene/content leakage, masks prompt tokens, bounds image tokens, and saves dataset hashes and validation loss in an adaptation manifest.

The training entry point expects JSONL rows with `scene_id`, `source`, `images`, `question`, and reference `answer`. The notebook explains preprocessing and split boundaries. Actual BigEarthNet.txt data, trained adapters, GPU execution, and benchmark results are **not bundled or claimed**.

To serve a trained model, merge/serve its adapter with the matching base model behind a compatible local endpoint, then set `MODEL_BACKEND=vllm`, `VLLM_BASE_URL`, and `VLLM_MODEL`. The configured model name is recorded in evidence. The generic fallback is not evidence of remote-sensing adaptation.

## Verification and limits

```sh
PYTHONPATH=. python -m pytest tests/test_reference_runtime.py tests/test_runtime_api.py tests/test_registry_contract.py tests/test_offline_routing.py -q
```

These tests run without a GPU and substitute a declared fake specialist for inference. They cover ingestion, deduplication, raster metadata, source-pixel preservation, ownership, pair legality, coordinate validation, bounded retries, durable execution records, failure recording, memory isolation and API contracts. Existing embedding integration tests require running Ollama and its embedding model.

Implemented: the storage separation, typed reference runtime, deterministic policy gates, registered task adapters, hybrid evidence retrieval, tiled caption indexing, bounded retry, scoped memory, and auditable persistence described above.

Still requiring implementation or empirical validation before claiming the full PDF/SIH target:

- Real remote-sensing adaptation and held-out VRSBench/RSVQA/CDVQA evaluation, plus genuine optical–SAR evaluation pairs.
- Dedicated optical/SAR/joint learned encoders and calibrated fusion/change specialists. Current paired models interpret display previews. Caption-derived tile embeddings are not physical sensor embeddings.
- Independent semantic verification and calibrated confidence. The verifier currently checks references and geometry; it leaves `verified=false`, does not assign an aggregate probability, and exposes unresolved conflicts. Bounded retries do not establish ground truth.
- A trained retrieval-grounding/reranking pipeline. MobileSAM grounding currently localizes from a whole-scene preview or user point. Candidate tile evidence is available but does not replace a specialized grounding model.
- Resumable LangGraph checkpoints, transactional queue outbox, cleanup/retention, per-user quotas, and multi-worker load testing. Execution snapshots persist, but interrupted jobs/graphs are not automatically resumed from an arbitrary node.
- Live integration testing of PostgreSQL/PostGIS, MinIO, Qdrant, Valkey/Celery, and actual inference. Local contract tests do not replace these checks.

## Primary references

- [BigEarthNet.txt](https://arxiv.org/abs/2603.29630)
- [Qwen2.5-VL model/processor](https://huggingface.co/docs/transformers/model_doc/qwen2_5_vl)
- [Qdrant query API and reciprocal-rank fusion](https://api.qdrant.tech/api-reference/search/query-points)
- [S3 object adapter interface](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)
