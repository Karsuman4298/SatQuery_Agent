"use client";

import { useState, useRef } from "react";
import { ImageMetadata } from "@/lib/types";

interface ImageViewerProps {
  imageId: string | null;
  imageMeta?: ImageMetadata;
  onRegionDrawn: (bounds: { x_min: number; y_min: number; x_max: number; y_max: number }) => void;
  evidenceOverlay?: any[]; 
  changeMaskUrl?: string | null;
}

export default function ImageViewer({ imageId, imageMeta, onRegionDrawn, evidenceOverlay = [], changeMaskUrl }: ImageViewerProps) {
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentPos, setCurrentPos] = useState({ x: 0, y: 0 });
  const [hoverLat, setHoverLat] = useState<number | null>(null);
  const [hoverLon, setHoverLon] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  // Helper to map mouse coordinates to lat/lon based on image bounds
  const updateGeoCoords = (x: number, y: number) => {
    if (!imageMeta || !imgRef.current) return;
    
    let minLon = 73.85; let minLat = 18.52;
    let maxLon = 73.95; let maxLat = 18.62;

    const bounds = imageMeta.bounds as any;
    if (bounds && bounds.coordinates && bounds.coordinates[0]) {
      const coords = bounds.coordinates[0];
      minLon = coords[0][0]; minLat = coords[0][1];
      maxLon = coords[2][0]; maxLat = coords[2][1];
    }

    const imgRect = imgRef.current.getBoundingClientRect();
    const containerRect = containerRef.current!.getBoundingClientRect();
    
    // Calculate relative position within the actual image bounds
    const relX = x - (imgRect.left - containerRect.left);
    const relY = y - (imgRect.top - containerRect.top);
    
    const pctX = relX / imgRect.width;
    const pctY = relY / imgRect.height;
    
    if (pctX >= 0 && pctX <= 1 && pctY >= 0 && pctY <= 1) {
      const lon = minLon + (maxLon - minLon) * pctX;
      // Y is inverted in screen space vs latitude space
      const lat = maxLat - (maxLat - minLat) * pctY;
      setHoverLon(lon);
      setHoverLat(lat);
    } else {
      setHoverLon(null);
      setHoverLat(null);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!containerRef.current || !imageId) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setIsDrawing(true);
    setStartPos({ x, y });
    setCurrentPos({ x, y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    updateGeoCoords(x, y);

    if (isDrawing) {
      setCurrentPos({ x, y });
    }
  };

  const handleMouseUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    
    const x_min = Math.min(startPos.x, currentPos.x);
    const x_max = Math.max(startPos.x, currentPos.x);
    const y_min = Math.min(startPos.y, currentPos.y);
    const y_max = Math.max(startPos.y, currentPos.y);
    
    if (x_max - x_min > 10 && y_max - y_min > 10) {
      onRegionDrawn({ x_min, y_min, x_max, y_max });
    }
    
    setStartPos({ x: 0, y: 0 });
    setCurrentPos({ x: 0, y: 0 });
  };

  return (
    <div className="relative w-full h-full bg-gray-900 overflow-hidden flex items-center justify-center rounded-xl border border-gray-800">
      
      {/* Top right coordinate overlay */}
      {hoverLat !== null && hoverLon !== null && (
        <div className="absolute top-4 right-4 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-gray-700 text-xs font-mono z-20 pointer-events-none flex gap-3 text-gray-300">
          <span>LAT: <span className="text-emerald-400">{hoverLat.toFixed(5)}</span></span>
          <span>LON: <span className="text-emerald-400">{hoverLon.toFixed(5)}</span></span>
        </div>
      )}

      {!imageId ? (
        <div className="text-gray-500">No image loaded</div>
      ) : (
        <div 
          ref={containerRef}
          className="relative w-full h-full cursor-crosshair flex items-center justify-center"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <img 
            ref={imgRef}
            src={`${API_BASE_URL}/images/${imageId}/tile`} 
            alt="Satellite tile" 
            className="max-w-full max-h-full object-contain pointer-events-none" 
            draggable={false}
          />
          
          {changeMaskUrl && (
            <img 
              src={changeMaskUrl} 
              alt="Change mask" 
              className="absolute inset-0 w-full h-full object-contain pointer-events-none opacity-50 mix-blend-screen" 
              draggable={false}
            />
          )}
          
          {isDrawing && (
            <div 
              className="absolute border-2 border-emerald-400 bg-emerald-400/20 pointer-events-none"
              style={{
                left: Math.min(startPos.x, currentPos.x),
                top: Math.min(startPos.y, currentPos.y),
                width: Math.abs(currentPos.x - startPos.x),
                height: Math.abs(currentPos.y - startPos.y),
              }}
            />
          )}

          {evidenceOverlay.map((ev, i) => {
            if (ev.type === "bbox" && ev.bbox) {
              return (
                <div 
                  key={i}
                  className="absolute border-2 border-amber-500 bg-amber-500/10 pointer-events-none transition-all duration-500"
                  style={{
                    left: ev.bbox.x_min,
                    top: ev.bbox.y_min,
                    width: ev.bbox.x_max - ev.bbox.x_min,
                    height: ev.bbox.y_max - ev.bbox.y_min,
                  }}
                >
                  <span className="absolute -top-6 left-0 bg-amber-500 text-black text-[10px] font-bold px-1.5 py-0.5 rounded shadow-lg whitespace-nowrap">
                    {ev.label} ({(ev.confidence * 100).toFixed(0)}%)
                  </span>
                </div>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}
