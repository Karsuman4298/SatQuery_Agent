"use client";

import { useState } from "react";
import { verifyFusion } from "@/lib/api";

interface FusionViewProps {
  opticalId: string;
  sarId: string;
}

export default function FusionView({ opticalId, sarId }: FusionViewProps) {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    setLoading(true);
    try {
      const res = await verifyFusion(opticalId, sarId);
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-x-0 top-0 bg-gray-900/90 border-b border-gray-800 p-4 shadow-2xl backdrop-blur-md rounded-b-xl z-20 m-4 mt-0">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-white flex items-center">
          Optical-SAR Cross-Validation
          {loading && <span className="ml-3 h-4 w-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />}
        </h3>
        {!result && !loading && (
          <button 
            onClick={handleVerify}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Run Verification
          </button>
        )}
      </div>
      
      {result && (
        <div className="flex gap-4 items-start">
          <div className="w-24 h-24 rounded-full border-4 border-indigo-500 flex items-center justify-center shrink-0 flex-col">
            <span className="text-2xl font-black text-indigo-400">{(result.agreement_pct).toFixed(0)}%</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest mt-1">Match</span>
          </div>
          <div className="flex-1 bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div className="text-sm text-gray-300 leading-relaxed">
              {result.verification_result}
            </div>
            
            <div className="mt-3 flex gap-2">
              <span className="bg-emerald-500/10 text-emerald-400 text-xs px-2 py-1 rounded border border-emerald-500/20 font-mono">
                Optical Features: {result.details?.optical_features_detected || "N/A"}
              </span>
              <span className="bg-indigo-500/10 text-indigo-400 text-xs px-2 py-1 rounded border border-indigo-500/20 font-mono">
                SAR Features: {result.details?.sar_features_detected || "N/A"}
              </span>
              <span className="bg-amber-500/10 text-amber-400 text-xs px-2 py-1 rounded border border-amber-500/20 font-mono">
                Matches: {result.details?.matched_features || "N/A"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
