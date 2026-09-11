"use client";

import { useState } from "react";
import { ZoomIn, ZoomOut, Maximize, Target } from "lucide-react";

interface ImageViewerProps {
  imageSrc: string | null;
  setImageSrc: (val: string | null) => void;
}

export default function ImageViewer({ imageSrc, setImageSrc }: ImageViewerProps) {
  // A dummy image if none provided for visual matching of the screenshot
  const displayImage = imageSrc || "/dummy-satellite.jpg"; 

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setImageSrc(url);
    }
  };

  return (
    <div className="relative w-full h-full bg-[#05080a] flex items-center justify-center p-8">
      
      {/* Upload Overlay (if we wanted one, or just let chat handle uploads) */}
      {!imageSrc && (
        <div className="absolute top-4 left-4 z-20">
          <label className="cursor-pointer bg-[#0a1815] hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">
            Upload Image
            <input type="file" className="hidden" accept="image/*" onChange={handleFileChange} />
          </label>
        </div>
      )}

      {/* Main Image Container */}
      <div className="relative w-[700px] h-[700px] max-w-full max-h-full rounded-3xl overflow-hidden border border-gray-800/80 shadow-2xl">
        <img 
          src={displayImage} 
          alt="Satellite Scene" 
          className="w-full h-full object-cover"
        />

        {/* Region Bounding Box Overlay */}
        <div className="absolute top-[30%] left-[35%] w-[30%] h-[40%] border-2 border-dashed border-emerald-400 bg-emerald-400/10 rounded-sm pointer-events-none">
          <div className="absolute -top-7 left-1/2 transform -translate-x-1/2 bg-emerald-400 text-black font-bold text-[11px] px-3 py-1 rounded shadow-lg tracking-wider whitespace-nowrap">
            REGION ALPHA
          </div>
        </div>
      </div>

      {/* Bottom Zoom Controls */}
      <div className="absolute bottom-8 flex items-center space-x-1 bg-[#0a0e14] border border-gray-800/60 rounded-full px-4 py-2 shadow-xl z-20">
        <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-gray-300 text-xs font-semibold px-2">100%</span>
        <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
          <ZoomIn className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-gray-800 mx-1"></div>
        <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
          <Target className="w-4 h-4" />
        </button>
        <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
          <Maximize className="w-4 h-4" />
        </button>
      </div>
      
    </div>
  );
}
