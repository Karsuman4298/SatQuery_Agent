export type AgentMode = "vqa" | "segmentation" | "change_detection" | "fusion" | "conversational";

export interface BaseAgentRequest {
  mode: AgentMode;
  question?: string;
}

export interface VqaRequest extends BaseAgentRequest {
  mode: "vqa";
  image_id: string;
  region_id?: string;
  question: string;
}

export interface SegmentationRequest extends BaseAgentRequest {
  mode: "segmentation";
  image_id: string;
  region_id?: string;
  question: string; // The object description to segment
}

export interface ChangeDetectionRequest extends BaseAgentRequest {
  mode: "change_detection";
  before_image_id: string;
  after_image_id: string;
  question?: string;
}

export interface FusionRequest extends BaseAgentRequest {
  mode: "fusion";
  optical_image_id: string;
  sar_image_id: string;
  question?: string;
}

export interface ConversationalRequest extends BaseAgentRequest {
  mode: "conversational";
  question: string;
  image_id?: string; // Optional context if they want to refer to the current image
}

export type AgentQueryPayload = VqaRequest | SegmentationRequest | ChangeDetectionRequest | FusionRequest | ConversationalRequest;

export interface TraceStep {
  step: string;
  status: "pending" | "running" | "completed" | "failed";
  data?: any;
}

export interface Evidence {
  type: string;
  bbox?: any;
  mask_url?: string;
  confidence: number;
  label?: string;
}

export interface AgentResponse {
  answer: string;
  confidence: number;
  evidence: Evidence[];
  errors: any[];
  change_mask?: string;
  change_pct?: number;
  agreement_pct?: number;
  segment_mask?: string;
}
