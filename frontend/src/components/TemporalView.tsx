"use client";

import { useState, useEffect } from "react";
import { submitTemporal, getChangeResult } from "@/lib/api";

interface TemporalViewProps {
  beforeImageId: string;
  afterImageId: string;
  onChangeMaskReceived?: (url: string | null) => void;
}

export default function TemporalView({ beforeImageId, afterImageId, onChangeMaskReceived }: TemporalViewProps) {
  const [changeId, setChangeId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function startJob() {
      setLoading(true);
      if (onChangeMaskReceived) onChangeMaskReceived(null);
      try {
        const res = await submitTemporal(beforeImageId, afterImageId);
        setChangeId(res.change_id);
      } catch (e) {
        console.error(e);
        setLoading(false);
      }
    }
    startJob();
  }, [beforeImageId, afterImageId, onChangeMaskReceived]);

  useEffect(() => {
    if (!changeId) return;

    const interval = setInterval(async () => {
      try {
        const res = await getChangeResult(changeId);
        setResult(res);
        if (res.status === "completed" || res.status === "failed") {
          clearInterval(interval);
          setLoading(false);
          if (res.status === "completed" && onChangeMaskReceived && res.change_mask_url) {
            onChangeMaskReceived(res.change_mask_url);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [changeId]);

  return (
    <div className="absolute top-4 right-4 bg-gray-900/95 border border-gray-700 p-6 shadow-2xl backdrop-blur-md rounded-xl z-20 w-[450px]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-black tracking-widest text-emerald-400 uppercase">
          Temporal Auto-Detection
        </h3>
        {loading && <span className="h-4 w-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />}
      </div>
      
      {result && result.status === "completed" ? (
        <div className="space-y-6">
          <div className="flex items-center space-x-4 border-b border-gray-800 pb-4">
            <div className="flex-1">
              <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-amber-500">
                {result.change_pct?.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-widest mt-1">Total Scene Change</div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">AI Impact Statistics</div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-950 p-3 rounded border border-gray-800">
                <div className="text-[10px] text-gray-500 uppercase">Population</div>
                <div className="text-lg font-mono text-emerald-400">{result.impact_stats?.affected_population?.toLocaleString() || "N/A"}</div>
              </div>
              <div className="bg-gray-950 p-3 rounded border border-gray-800">
                <div className="text-[10px] text-gray-500 uppercase">Buildings</div>
                <div className="text-lg font-mono text-amber-400">{result.impact_stats?.affected_buildings?.toLocaleString() || "N/A"}</div>
              </div>
              <div className="bg-gray-950 p-3 rounded border border-gray-800">
                <div className="text-[10px] text-gray-500 uppercase">Roads (km)</div>
                <div className="text-lg font-mono text-indigo-400">{result.impact_stats?.affected_roads_km?.toFixed(2) || "N/A"}</div>
              </div>
              <div className="bg-gray-950 p-3 rounded border border-gray-800">
                <div className="text-[10px] text-gray-500 uppercase">Area (sq km)</div>
                <div className="text-lg font-mono text-white">{result.impact_stats?.affected_area_sqkm?.toFixed(2) || "N/A"}</div>
              </div>
            </div>
          </div>
        </div>
      ) : result && result.status === "failed" ? (
        <div className="text-red-400 text-sm">Failed to compute change detection: {result.error_message}</div>
      ) : (
        <div className="text-gray-400 text-sm flex items-center space-x-3">
          <span>Computing impact statistics via Siam-UNet...</span>
        </div>
      )}
    </div>
  );
}
