# SatQuery — Earth Observation Intelligence Platform

**SatQuery** is an interactive, low-latency agentic web application designed for multi-modal Earth Observation (EO) satellite image analysis. Built to meet the requirements of public benchmark test splits and the **ISRO / SAC Evaluation Standard**, SatQuery enables users to seamlessly upload EO imagery (single optical/multispectral, bi-temporal pairs, or co-registered optical–SAR pairs), draw interactive regions of interest, and run a **Multi-Agent AI System** for Visual Question Answering (VQA), Temporal Change Analysis, Optical-SAR Joint Fusion, and Interactive Segmentation.

---

## 📌 Executive Summary of Progress

The SatQuery platform has evolved from initial UI prototyping into a fully functional, containerized **Agentic Earth Observation System**. All key system capabilities—including front-end geospatial canvas interactions, FastAPI backend routing, PostGIS spatial persistence, and the **LangGraph Multi-Agent Model Server**—are fully built and integrated.

### Key Milestones Achieved:
- **Phase 1 & 2 (UI & Infrastructure)**: Integrated Next.js 14 IDE-style workspace with resizable panels, real-time bounding box drawing, rasterio-driven lat/lon calculations, and Server-Sent Events (SSE) streaming.
- **Phase 3 (Multi-Agent Orchestration)**: Implemented a production-grade **LangGraph orchestrator** with intelligent routing powered by LLM decision-making (`Qwen2.5-72B-Instruct`) and fallback heuristic nodes.
- **Task-Specific Tool Engines**: Implemented standardized tools for **VQA**, **Change Detection**, **Optical-SAR Fusion**, and **Click Segmentation**.
- **ISRO/SAC & Public Benchmark Alignment**: Designed data pipelines and evaluation structures for co-registered **Cartosat-2S Optical** & **RISAT SAR** pairs, bi-temporal pairs, and standard benchmarks (BigEarthNet, RSVQA, GeoChat).
- **Dependency & Build Harmonization**: Resolved complex Pydantic v2 / FastAPI / LangChain version constraints, enabling automated multi-container Docker deployments.

---

## 🏗️ System Architecture

SatQuery follows a microservices architecture across 4 isolated Docker containers to guarantee operational separation, horizontal scalability, and developer parallelization.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SatQuery Workspace UI                          │
│                   Next.js 14 + Canvas + Mapbox HUD                      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                           HTTP / SSE Streaming
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Backend API Service (FastAPI)                    │
│          • Image upload & Rasterio spatial metadata extraction          │
│          • Query orchestration & Session management                     │
└──────────────────┬──────────────────────────────────┬───────────────────┘
                   │                                  │
          SQLAlchemy / PostGIS                        │ REST / JSON
                   │                                  ▼
┌──────────────────▼───────────┐    ┌────────────────────────────────────┐
│      PostgreSQL + PostGIS    │    │      Model Server Container        │
│  • Bounding box geometries   │    │  (FastAPI + LangGraph Multi-Agent) │
│  • Image metadata storage    │    │  ┌──────────────────────────────┐  │
│  • Spatial index queries     │    │  │ LangGraph Router Node        │  │
└──────────────────────────────┘    │  └──────────────┬───────────────┘  │
                                    │                 │                      │
                                    │  ┌──────────────▼───────────────┐  │
                                    │  │ LangGraph Executor & Tools   │  │
                                    │  │ • VQA Engine                 │  │
                                    │  │ • Change Analysis Engine     │  │
                                    │  │ • Optical-SAR Fusion Engine  │  │
                                    │  │ • Click-Segmentation Engine  │  │
                                    │  └──────────────────────────────┘  │
                                    └────────────────────────────────────┘
```

---

## 🤖 Multi-Agent System (LangGraph Architecture)

The core intelligence layer lives inside `model-server/app/agent/` and is orchestrated using **LangGraph**.

### 1. Router Node (`graph.py`)
- **LLM Decision Engine**: Evaluates the user query, conversation history, and uploaded image metadata (single image, before/after pair, optical+SAR, or click point).
- **Model**: Invokes `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API to select the optimal analysis tool and return structured JSON decisions.
- **Rule-Based Fallback Engine**: If cloud API network conditions fluctuate, the router gracefully falls back to deterministic context evaluation (e.g., automatically routing temporal pairs to `change_detection` and optical-SAR pairs to `fusion`).

### 2. Specialized Tool Suite (`tools.py`)
| Tool Name | Engine Function | Target Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`vqa_tool`** | Single-image Visual Question Answering & object detection | Single Optical / SAR image | Natural language answer, bounding boxes, impact metrics |
| **`change_analysis_tool`** | Bi-temporal change detection & extent calculation | Before / After GeoTIFF pair | Change summary, change ratio (%), highlight bounding boxes |
| **`fusion_analysis_tool`** | Optical-SAR joint cross-verification & radar analysis | Co-registered Optical + SAR pair | Multi-modal confirmation text, agreement score (%) |
| **`segmentation_tool`** | Point-guided boundary segmentation | Image + [x, y] coordinates | Segmentation mask polygon overlays |

---

## 🚀 Key Features Implemented

### 1. Interactive Geospatial Workspace (Frontend)
- **Multi-Modal Auto-Detection**: Uploading image pairs automatically detects whether they represent a **Temporal Pair** (revealing the side-by-side comparison slider) or a **Fusion Pair** (revealing Optical vs SAR toggles).
- **Live Lat/Lon HUD**: Hovering over the map or drawing bounding boxes calculates real-world geographic coordinates derived from GeoTIFF raster transformation matrices (`rasterio`).
- **Dynamic Region Switching**: Users can draw multiple Regions of Interest (ROIs), hot-swap between them in the sidebar, and target queries specifically to an ROI.

### 2. Streaming Thought Traces & Bounding Box Evidence
- **Real-Time SSE Pipeline**: The UI streams agent reasoning traces, model execution status, and text tokens live without full page refreshes.
- **Visual Evidence Overlays**: Detected objects (e.g., flooded buildings, infrastructure, vessels) are returned with bounding box coordinates and rendered dynamically as glowing vector overlays on the image canvas.
- **Impact Statistics**: Automated calculation of affected population and structural impact figures for disaster evaluation queries.

### 3. ISRO/SAC Benchmark & Dataset Support
- Designed to support prescribed benchmark test splits (e.g., BigEarthNet, RSVQA, GeoChat).
- Built-in schema for **ISRO/SAC evaluation datasets** containing pre-georeferenced, co-registered **Cartosat-2S Optical** and **RISAT SAR** image pairs.

---

## 🛠️ API Reference & Endpoint Map

### Backend Service (`http://localhost:8000`)
- `POST /api/v1/upload`: Processes GeoTIFF upload, extracts CRS/transform metadata, saves to disk & PostGIS.
- `POST /api/v1/query`: Accepts user query, image ID(s), and region context. Streams agent execution responses via Server-Sent Events (SSE).
- `GET /api/v1/images/{id}`: Retrieves image details and PostGIS spatial geometry.

### Model Server (`http://localhost:8001`)
- `POST /agent/query`: Primary endpoint invoked by Backend; triggers the **LangGraph orchestrator**.
- `POST /vqa/predict`: Direct single-image VQA model execution.
- `POST /change/predict`: Direct bi-temporal change detection execution.
- `POST /fusion/predict`: Direct optical-SAR joint fusion inference.
- `POST /segment/predict`: Direct click-guided segmentation inference.

---

## ⚖️ Evaluation & Judging Criteria Matrix

| Criterion | Evaluation Metric | Supported Data / Benchmark | Status |
| :--- | :--- | :--- | :--- |
| **VQA Accuracy** | Open-ended BLEU/ROUGE & classification accuracy | RSVQA, GeoChat test split | Fully Supported |
| **Change Extent Precision** | IoU / F1-Score on change masks | Bi-temporal GeoTIFF pairs | Fully Supported |
| **Optical-SAR Agreement** | Cross-modal feature alignment score | Cartosat-2S + RISAT SAR | Fully Supported |
| **System Latency** | SSE initial token response time (<2s target) | Asynchronous FastAPI + Docker | Optimized |

---

## 🌐 Infrastructure & Deployment Notes

### Hugging Face API Integration & Local Fallback
During deployment probing, the system was configured to interact with Hugging Face's serverless endpoints:
- **Router Model**: `Qwen/Qwen2.5-72B-Instruct` is utilized via the Serverless Router endpoint (`router.huggingface.co`) for natural language agent orchestration.
- **Vision Models**: Model server tools feature built-in fallback routines to local PyTorch pipelines or structured heuristic responses if cloud vision APIs experience rate-limits or DNS constraints.

### Multi-Container Quickstart

Ensure Docker Desktop is installed and running, then start all 4 services:

```bash
# Build and bring up all microservices
docker compose up --build -d
```

#### Service URLs:
- **Frontend Workspace**: `http://localhost:3000`
- **Backend API Documentation**: `http://localhost:8000/docs`
- **Model Server API Documentation**: `http://localhost:8001/docs`

---

## 📅 Roadmap & Next Steps

1. **Local VLM Model Weight Fine-Tuning**: Integrate local Qwen2-VL or GeoChat PyTorch model weights directly into `model-server` GPU VRAM for offline hackathon judging.
2. **PostGIS Session Memory**: Persist multi-turn conversation threads into database tables (`chat_sessions`) for historical context retrieval.

# SatQuery_Agent
