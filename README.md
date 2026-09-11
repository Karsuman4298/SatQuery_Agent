# SatQuery — Comprehensive Technical Documentation & Architecture

Welcome to the definitive technical reference for **SatQuery**, an interactive, low-latency agentic web application designed for multi-modal Earth Observation (EO) satellite image analysis. This document serves as an exhaustive guide to the platform's architecture, tools, technologies, and the intricate agentic systems powering its intelligence.

---

## 1. Executive Summary & Vision

SatQuery bridges the gap between raw satellite imagery and actionable geospatial intelligence. By leveraging a modern React-based frontend and a high-performance Python/FastAPI backend, users can upload EO imagery (Optical, SAR, Multispectral, Thermal) and interact with an AI assistant (GeoChat) to analyze the data.

At the heart of SatQuery is a **Multi-Agent Orchestration System** powered by LangGraph and state-of-the-art Vision-Language Models (VLMs) hosted via Cloudflare Workers AI. This system dynamically routes natural language queries to specialized computer vision tools—ranging from Visual Question Answering (VQA) to zero-shot pixel-perfect segmentation using MobileSAM.

---

## 2. Frontend Architecture (React, Vite, TSX)

The frontend is a Single Page Application (SPA) built for extreme interactivity and real-time feedback.

### 2.1 Core Technologies
- **Framework**: React 18, utilizing functional components and hooks.
- **Build Tool**: Vite for lightning-fast HMR and optimized production bundling.
- **Language**: TypeScript (TSX) for strict type safety across components and API payloads.
- **Styling**: Pure vanilla CSS utilizing modern glassmorphism (translucent backgrounds with blur), sleek dark-mode aesthetics, and responsive CSS Grid/Flexbox layouts. No bulky CSS frameworks are used, ensuring maximum performance and customizability.

### 2.2 Component Structure & Workspace
- **WorkspacePage (`WorkspacePage.tsx`)**: The central hub of the application. It manages a three-panel layout:
  - **Left Panel (Metadata)**: Displays detected image modalities, spectral channels, observation summaries, and active regions.
  - **Center Panel (Interactive Canvas)**: Renders the satellite image with dynamic zooming, panning, and layer filtering. 
  - **Right Panel (GeoChat UI)**: The conversational interface where users interact with the agent.
- **Interactive Canvas & Click-to-Segment**: 
  The center image wrapper captures `onClick` events, mathematically translating the user's browser viewport click into exact normalized image coordinates `[x, y]`. A glowing blue crosshair/dot is rendered at this coordinate, and the `clickPoint` state is updated to be dispatched to the backend upon the next user query.
- **Mask Overlays**: 
  When the backend successfully segments an object, it returns a transparent Base64 PNG. The frontend extracts this and dynamically renders it as an absolutely positioned `<img>` overlay (`.workspace-mask-overlay`) exactly on top of the original satellite image, maintaining perfect aspect ratio alignment regardless of zoom level.

### 2.3 GeoChat Conversational UI
- **State Management**: Chat messages are maintained in a React state array. Each `Message` interface tracks the sender, text, timestamp, generated `segment_mask`, and structured `evidence`.
- **Evidence Rendering**: To combat AI hallucination, the GeoChat UI features a dedicated `.geochat-evidence-container`. When the backend returns verifiable claims, the UI maps over the `evidence` array and renders each claim explicitly below the AI's response, complete with confidence scores.

---

## 3. Backend Architecture (FastAPI, Uvicorn)

The backend acts as the secure, high-throughput gateway between the frontend client and the AI orchestration layer.

### 3.1 Core Technologies
- **Framework**: FastAPI (Python 3.9+) for highly concurrent, async RESTful endpoints.
- **Server**: Uvicorn ASGI server.
- **Validation**: Pydantic v2 for rigorous schema validation of all incoming and outgoing API payloads.

### 3.2 API Endpoints & Routing
- `POST /api/v1/upload`: 
  Handles multipart form data for image uploads. It decodes the files, performs heuristic checks on file extensions and headers, and provisions a unique session ID.
- `POST /agent`: 
  The primary query endpoint. It accepts an `AgentQueryOptions` JSON payload (containing the user's question, Base64 image data, chat history, and optional `click_point`). It instantiates the LangGraph initial state and asynchronously invokes the multi-agent graph.
- `GET /health`: 
  A standard liveness probe for Docker container orchestration and load balancer checks.

### 3.3 Data Processing
Images are transmitted between the frontend and backend using Base64 encoding. The backend handles decoding these strings into in-memory byte buffers (`io.BytesIO`) which are then natively processed by PIL (Pillow) and NumPy for computer vision tasks, entirely bypassing slow disk I/O.

---

## 4. Database & Authentication (Supabase)

SatQuery relies on Supabase (an open-source Firebase alternative) for its persistent storage and identity management.

### 4.1 Authentication
- Integrates Supabase Auth for seamless user sign-ups, logins, and JWT token management.
- The React frontend uses the `AuthContext` to track session state. Upon successful login, the session is securely cached in local storage.
- All subsequent HTTP requests to protected FastAPI endpoints include the Supabase JWT in the `Authorization: Bearer` header.

### 4.2 Data Flow & Relational Database (PostgreSQL)
The application handles complex user-scoped data using PostgreSQL. The flow is as follows:
1. **User Table Sync**: When a user registers via Supabase Auth, a PostgreSQL trigger automatically provisions a corresponding row in the `public.users` table, setting up their profile metadata and API quotas.
2. **Analysis Metadata (`analyses` table)**: 
   - When a user uploads an image via the frontend `WorkspacePage`, it is sent to the FastAPI backend.
   - The backend validates the image and inserts a new row into the `analyses` table, containing the image metadata (dimensions, modality, file size).
   - The primary key (`id`) of this row acts as the `session_id` for the analysis.
3. **Chat History (`chat_messages` table)**:
   - As the user chats with the AI, the frontend sends queries to the `/agent` endpoint.
   - Upon receiving the AI's response, the backend serializes the interaction and inserts it into the `chat_messages` table with a foreign key linking back to the `analyses` table.
   - This ensures full persistence. When the user visits the History page, the frontend fetches these rows so the user can resume precisely where they left off.
4. **Row Level Security (RLS)**:
   - Supabase RLS policies are strictly enforced on all tables. 
   - Each SQL query automatically filters rows where `auth.uid() = user_id`, guaranteeing that users can only ever access their own uploaded images and chat histories.

### 4.3 Object Storage & Media Flow
- **Raw Imagery**: When images are uploaded, the FastAPI backend streams them directly into a secure Supabase Storage bucket (`satquery-imagery`). Only the secure CDN URL is stored in the PostgreSQL database.
- **Segmentation Masks**: When the MobileSAM agent generates a Base64 segmentation mask, the backend uploads it to a `satquery-masks` bucket. This prevents the PostgreSQL database from bloating with heavy Base64 strings, maintaining lightning-fast query times.
- Both buckets are protected by RLS, ensuring private images remain completely isolated per user account.

---

## 5. Agentic AI System & LangGraph Orchestration

The crown jewel of SatQuery is its autonomous, multi-agent reasoning engine located in `model-server/app/agent/`. It utilizes LangGraph to create a robust StateGraph that manages context, tools, and LLM inferences.

### 5.1 The State Object (`GraphState`)
LangGraph operates on a shared state passed between nodes. Our `GraphState` (defined via Pydantic) contains:
- `messages`: A chronological log of human and AI messages.
- `mode`: The current operational mode (e.g., `router`, `vqa`, `segmentation`).
- `image` & `click_point`: The visual context.
- `evidence`: A structured list of verifiable facts.
- `segment_mask`: Base64 PNG output from the segmentation engine.
- `missing_inputs`: Flags tracking if the user requested an action but forgot to supply necessary inputs (e.g., asking for change detection with only one image).

### 5.2 Cloudflare Workers AI Integration
We utilize Cloudflare Workers AI for edge-optimized inference, drastically reducing latency.
- **Model**: `Qwen/Qwen2.5-VL` (a highly capable Vision-Language Model).
- **Client**: `cloudflare_client.py` wraps the standard HTTP requests to Cloudflare's `/run` endpoint, handling retries, timeout management, and JSON schema parsing for structured generation.

### 5.3 The Conversational Router Node
This node acts as the "Brain" of the system. 
- **Prompt Engineering**: The router is injected with a powerful system prompt that explains its role as an EO orchestrator. It is given access to the user's query, the chat history, and a heuristic classifier's recommendation.
- **Routing Logic**: The router evaluates if the user's query is conversational ("hello") or analytical ("segment the river"). It explicitly prioritizes the classifier's suggested tool, mitigating infinite loops. If inputs are missing (e.g., change detection requested but no second image provided), the router intelligently aborts the tool call and routes to the conversational fallback to ask the user for the missing data.

### 5.4 Specialized Tool Nodes

#### A. Visual Question Answering (`vqa_tool`)
- **Execution**: Sends the user's query and the image to Qwen2.5-VL. 
- **Output**: Generates a detailed textual analysis of the scene (e.g., identifying land cover, estimating crop health, or detecting infrastructure).

#### B. Segmentation Engine (`segmentation_tool`)
The segmentation engine utilizes Ultralytics' **MobileSAM** (Segment Anything Model) for zero-shot object masking. It is highly optimized to prevent hallucination through a dual-input strategy:
- **Explicit Click Points**: If the user clicks the image, the exact `[x, y]` coordinate is received. The engine scales this coordinate to the image's dimensions and passes it as a precise prompt to MobileSAM.
- **Natural Language Localization**: If the user types "segment the river" without clicking, the VLM is invoked to localize the river. The VLM returns a bounding box and a central `point_x, point_y`.
- **Anti-Hallucination Fallback**: Previous iterations passed massive bounding boxes to SAM, causing it to segment the entire background. The current architecture strictly enforces **point-based prompting**. If the VLM only provides a bounding box, the backend calculates the exact mathematical center (`cx, cy`) of that box and feeds *only that single coordinate* to SAM. This guarantees that SAM focuses on the specific object rather than the bounding box's background noise.
- **Post-Processing**: The generated binary mask array is colorized (RGBA Emerald-400), converted to a transparent PNG, and returned as a Base64 string to the frontend. A cropped image of the segmented object is also captioned by the VLM for further context.

#### C. Fusion & Change Analysis Tools
- **Change Detection**: Analyzes bi-temporal image pairs (Before/After) to calculate percentage changes in land cover or disaster impact (e.g., flood extent).
- **SAR-Optical Fusion**: Cross-references optical imagery with Synthetic Aperture Radar (SAR) data to penetrate cloud cover and verify ground features.

### 5.5 The Conversational Aggregator Node
After a specialized tool finishes its execution, the raw outputs (confidence scores, raw masks, tool names) are passed to the `conversational_aggregator_node`. This node uses the VLM to synthesize the technical outputs into a friendly, conversational response tailored to the user, ensuring the final output is both scientifically accurate and highly readable.

---

## 6. Evidence-Based Anti-Hallucination Framework

To maintain scientific integrity, SatQuery implements a rigorous evidence pipeline to prevent LLM hallucinations.
1. **Prompt Constraint**: During `vqa` or aggregation, the VLM is instructed to populate a strict JSON schema array named `evidence`.
2. **Schema Definition**: Each evidence item requires a `claim_id`, a `source_type` (observation vs. interpretation), and a `text` field containing the explicit claim (e.g., "River meandering through agricultural fields").
3. **Frontend Parsing**: The React frontend maps over this JSON array. Instead of dumping raw JSON strings to the user, it cleanly parses the `text` field and renders it under an "Evidence Found" UI badge. This forces the AI to "show its work," ensuring every claim can be traced back to a specific visual observation.

---

## 7. Setup, Development & Deployment

### 7.1 Environment Variables
Create a `.env` file in the `model-server` directory with the following critical keys:
```env
CLOUDFLARE_API_TOKEN=your_cloudflare_token
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
```

### 7.2 Running Locally (Native)
**Backend**:
```bash
cd model-server
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

### 7.3 Docker Deployment
SatQuery is fully containerized for production deployment across 4 isolated microservices.
```bash
# Build and start all containers in detached mode
docker compose up --build -d

# View live AI reasoning logs
docker compose logs -f model-server

# Gracefully shut down
docker compose down
```

---

## 8. Future Roadmap

1. **Local VLM Model Weight Fine-Tuning**: Integration of localized Qwen2-VL PyTorch model weights directly into GPU VRAM for entirely offline, air-gapped environments.
2. **Advanced Multi-Point SAM Prompts**: Expanding the localization pipeline to generate multiple positive and negative point prompts for complex, disjointed structures (e.g., archipelagos).
3. **Vector Database Integration**: Embedding chat histories and extracted evidence into Pinecone/Milvus for semantic RAG (Retrieval-Augmented Generation) across past sessions.
