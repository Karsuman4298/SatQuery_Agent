"use client";

import { useState, useRef, useEffect } from "react";
import { streamQuery, fetchQueries, getReportUrl } from "@/lib/api";
import { Download } from "lucide-react";

interface ChatPanelProps {
  imageId: string | null;
  activeRegionId: string | null;
  activeRegionName: string | null;
  onEvidenceReceived: (evidence: any[]) => void;
}

interface Message {
  id: string;
  dbId?: string;
  role: "user" | "assistant";
  content: string;
  trace?: { step_name: string; status: string; duration_ms: number }[];
  isReport?: boolean;
}

export default function ChatPanel({ imageId, activeRegionId, activeRegionName, onEvidenceReceived }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!imageId) {
      setMessages([]);
      return;
    }
    
    let isMounted = true;
    const loadHistory = async () => {
      try {
        const history = await fetchQueries(imageId);
        if (!isMounted) return;
        
        const formattedMessages: Message[] = [];
        for (const q of history) {
          formattedMessages.push({
            id: `user-${q.id}`,
            role: "user",
            content: q.question
          });
          if (q.answer) {
            formattedMessages.push({
              id: `asst-${q.id}`,
              dbId: q.id,
              role: "assistant",
              content: q.answer
            });
          }
        }
        setMessages(formattedMessages);
      } catch (e) {
        console.error("Failed to load history", e);
        if (isMounted) setMessages([]);
      }
    };
    loadHistory();
    
    return () => { isMounted = false; };
  }, [imageId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !imageId || isStreaming) return;

    const question = input.trim();
    setInput("");
    
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: question };
    const asstMsgId = (Date.now() + 1).toString();
    const asstMsg: Message = { id: asstMsgId, role: "assistant", content: "", trace: [] };
    
    setMessages((prev) => [...prev, userMsg, asstMsg]);
    setIsStreaming(true);
    
    onEvidenceReceived([]);

    try {
      const response = await streamQuery(imageId, question, activeRegionId || undefined);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      
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
          
          if (event && data) {
            const parsed = JSON.parse(data);
            
            if (event === "stage") {
              setMessages((prev) => prev.map(m => {
                if (m.id === asstMsgId) {
                  const trace = [...(m.trace || [])];
                  const stageTrace = {
                    step_name: parsed.stage,
                    status: parsed.status,
                    duration_ms: 0,
                  };
                  const existingIdx = trace.findIndex(t => t.step_name === parsed.stage);
                  if (existingIdx >= 0) trace[existingIdx] = stageTrace;
                  else trace.push(stageTrace);
                  const answer = parsed.data?.answer;
                  const dbId = parsed.data?.query_id;
                  return {
                    ...m,
                    trace,
                    ...(typeof answer === "string" ? { content: answer } : {}),
                    ...(typeof dbId === "string" ? { dbId } : {}),
                  };
                }
                return m;
              }));
              const reportEvidence = parsed.data?.evidence;
              if (Array.isArray(reportEvidence)) {
                onEvidenceReceived(reportEvidence);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Query stream error:", err);
      setMessages((prev) => prev.map(m => 
        m.id === asstMsgId ? { ...m, content: m.content + "\n\nError: Failed to fetch response." } : m
      ));
    } finally {
      setIsStreaming(false);
    }
  };

  const handleGenerateReport = async () => {
    // Find the last assistant message with a valid DB ID
    const lastAsst = [...messages].reverse().find(m => m.role === "assistant" && m.dbId && !m.isReport);
    if (!lastAsst || !lastAsst.dbId) return;

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const res = await fetch(`${API_BASE_URL}/reports/${lastAsst.dbId}?format=geojson`);
      if (!res.ok) throw new Error("Failed to fetch GeoJSON");
      const geojson = await res.text();
      
      const newMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: `Here is the GeoJSON report for the latest analysis:\n\n\`\`\`json\n${geojson}\n\`\`\``,
        dbId: lastAsst.dbId,
        isReport: true
      };
      setMessages(prev => [...prev, newMsg]);
    } catch (e) {
      console.error(e);
    }
  };

  const hasQueries = messages.some(m => m.role === "assistant" && m.dbId);

  return (
    <div className="flex flex-col h-full bg-gray-900 overflow-hidden text-sm">
      <div className="p-4 border-b border-gray-800 flex-shrink-0 flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-white">GeoChat</h3>
          <p className="text-xs text-emerald-500 font-mono mt-1">
            {activeRegionId ? `Target: ${activeRegionName || "Selected Region"}` : `Target: Full Scene`}
          </p>
        </div>
        {hasQueries && (
          <button 
            onClick={handleGenerateReport}
            className="flex items-center space-x-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold transition-colors shadow-lg"
          >
            <Download className="w-3 h-3" />
            <span>Generate Report</span>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="text-gray-500 text-center mt-10">
            Ask questions about the uploaded satellite imagery or drawn regions.
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            
            {msg.role === "assistant" && msg.trace && msg.trace.length > 0 && (
              <div className="mb-2 w-full max-w-[90%] rounded-lg bg-black/40 border border-gray-800 p-3 text-xs font-mono text-gray-400">
                {msg.trace.map((t, i) => (
                  <div key={i} className="flex items-center space-x-2 py-0.5">
                    {t.status === "running" ? (
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
                    ) : t.status === "completed" ? (
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                    )}
                    <span>{t.step_name}</span>
                    {t.duration_ms > 0 && <span className="opacity-40">[{t.duration_ms}ms]</span>}
                  </div>
                ))}
              </div>
            )}

            <div 
              className={`max-w-[90%] rounded-2xl px-4 py-3 leading-relaxed whitespace-pre-wrap ${
                msg.role === "user" 
                  ? "bg-indigo-600 text-white rounded-br-none" 
                  : "bg-gray-800 text-gray-200 border border-gray-700 rounded-bl-none"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && !msg.content && isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-emerald-500 animate-pulse" />
              )}
            </div>
            {msg.isReport && msg.dbId && (
              <div className="mt-2 ml-2 flex">
                <a 
                  href={getReportUrl(msg.dbId, "pdf")} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1 text-[10px] uppercase font-bold tracking-wider text-red-400 hover:text-red-300 transition-colors"
                >
                  <Download className="w-3 h-3" />
                  <span>Download PDF Report</span>
                </a>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!imageId || isStreaming}
            placeholder={imageId ? "Ask a question..." : "Upload an image first"}
            className="w-full bg-gray-950 text-white rounded-full pl-4 pr-12 py-3 border border-gray-700 focus:outline-none focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm shadow-inner"
          />
          <button
            type="submit"
            disabled={!input.trim() || !imageId || isStreaming}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full disabled:opacity-50 transition-colors shadow-lg"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
