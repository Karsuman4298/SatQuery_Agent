import { useState, useRef, useCallback } from "react";
import { AgentQueryPayload, AgentResponse, TraceStep, Evidence } from "../types/agent";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface UseAgentQueryReturn {
  submitQuery: (payload: AgentQueryPayload) => Promise<void>;
  isStreaming: boolean;
  trace: TraceStep[];
  response: AgentResponse | null;
  error: string | null;
  reset: () => void;
}

export function useAgentQuery(): UseAgentQueryReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setIsStreaming(false);
    setTrace([]);
    setResponse(null);
    setError(null);
  }, []);

  const submitQuery = useCallback(async (payload: AgentQueryPayload) => {
    setIsStreaming(true);
    setTrace([]);
    setResponse(null);
    setError(null);

    try {
      const url = new URL(`${API_BASE_URL}/agent/`);
      const res = await fetch(url.toString(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed with status ${res.status}`);
      }

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      
      let finalResponse: Partial<AgentResponse> = {
        answer: "",
        evidence: [],
        errors: [],
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        
        for (const part of parts) {
          const lines = part.split("\n");
          let event = "";
          let data = "";
          
          for (const line of lines) {
            if (line.startsWith("event: ")) event = line.slice(7);
            if (line.startsWith("data: ")) data = line.slice(6);
          }
          
          if (event === "stage" && data) {
            const parsed = JSON.parse(data);
            
            // Update trace
            setTrace(prev => {
              const newTrace = [...prev];
              const stageTrace: TraceStep = {
                step: parsed.stage,
                status: parsed.status,
                data: parsed.data
              };
              const existingIdx = newTrace.findIndex(t => t.step === parsed.stage);
              if (existingIdx >= 0) {
                newTrace[existingIdx] = stageTrace;
              } else {
                newTrace.push(stageTrace);
              }
              return newTrace;
            });
            
            // Check for final report data
            if (parsed.stage === "report_generator" && parsed.status === "complete") {
              finalResponse = {
                ...finalResponse,
                ...parsed.data
              };
              setResponse(finalResponse as AgentResponse);
            }

            // Check for errors
            if (parsed.stage === "error_responder") {
               setError(parsed.data?.error || "Unknown error occurred");
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Query stream error:", err);
      setError(err.message || "Failed to submit query");
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return {
    submitQuery,
    isStreaming,
    trace,
    response,
    error,
    reset,
  };
}
