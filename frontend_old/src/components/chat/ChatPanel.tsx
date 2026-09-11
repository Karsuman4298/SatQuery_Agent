"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot } from "lucide-react";
import { streamQuery } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  modelUsed?: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "assistant",
      content: "Multispectral analysis complete. NDVI vegetation index indicates 78.4% healthy canopy coverage with localized moisture variance in Sector 4.",
      modelUsed: "GPT-Vision RS"
    }
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentModel, setCurrentModel] = useState("GPT-Vision RS");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const question = input.trim();
    setInput("");
    
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: question };
    const asstMsgId = (Date.now() + 1).toString();
    const asstMsg: Message = { id: asstMsgId, role: "assistant", content: "" };
    
    setMessages((prev) => [...prev, userMsg, asstMsg]);
    setIsStreaming(true);

    try {
      // In a real app we'd pass the actual uploaded imageId. 
      // Using a dummy ID or just calling without one for the sake of the UI demo.
      const response = await streamQuery("dummy_id", question);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let latestModel = currentModel;
      
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
              const answer = parsed.data?.answer;
              const execSummary = parsed.data?.execution_summary;
              
              if (execSummary?.model_used) {
                latestModel = execSummary.model_used;
                setCurrentModel(latestModel);
              }

              setMessages((prev) => prev.map(m => {
                if (m.id === asstMsgId) {
                  return {
                    ...m,
                    ...(typeof answer === "string" ? { content: answer } : {}),
                    modelUsed: latestModel
                  };
                }
                return m;
              }));
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

  return (
    <div className="flex flex-col h-full bg-[#0a0e14] border-l border-gray-800/60 font-sans">
      
      {/* Chat Header */}
      <div className="p-5 border-b border-gray-800/60 flex items-center space-x-3 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
          <Bot className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-200 text-sm tracking-wide">GeoChat AI Assistant</h3>
          <p className="text-xs text-emerald-400/90 font-medium mt-0.5 flex items-center">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
            Model Online • {currentModel}
          </p>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
            <div 
              className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed text-sm ${
                msg.role === "user" 
                  ? "bg-[#0a1815] text-emerald-100 border border-emerald-500/30 rounded-tr-sm shadow-md" 
                  : "bg-[#0f141a] text-gray-300 border border-gray-800/80 rounded-tl-sm shadow-md"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && !msg.content && isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-emerald-500 animate-pulse" />
              )}
            </div>
            {msg.role === "assistant" && msg.content && (
              <div className="text-[10px] text-gray-600 mt-1.5 ml-1 font-medium">Just now</div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="p-4 bg-[#0a0e14] border-t border-gray-800/60 flex-shrink-0">
        <form 
          onSubmit={handleSubmit}
          className="relative flex items-center bg-[#05080a] border border-gray-800 rounded-full px-4 py-2 focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/30 transition-all shadow-inner"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this satellite scene..."
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 focus:outline-none py-1.5"
            disabled={isStreaming}
          />
          <button 
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 hover:text-emerald-300 disabled:opacity-50 transition-colors ml-2"
          >
            <Send className="w-4 h-4 translate-x-[-1px] translate-y-[1px]" />
          </button>
        </form>
      </div>
      
    </div>
  );
}
