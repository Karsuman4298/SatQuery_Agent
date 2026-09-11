"use client";

import { Satellite, ArrowLeft, Download, Share2, CheckCircle2 } from "lucide-react";
import LeftSidebar from "@/components/layout/LeftSidebar";
import ImageViewer from "@/components/viewer/ImageViewer";
import ChatPanel from "@/components/chat/ChatPanel";
import { useState } from "react";

export default function Home() {
  const [activeImage, setActiveImage] = useState<string | null>(null);

  return (
    <main className="flex flex-col h-screen w-full bg-[#080c10] text-gray-300 font-sans overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-gray-800/60 bg-[#0a0e14] flex items-center justify-between px-4 flex-shrink-0 z-10">
        
        {/* Left: Dashboard & Logo */}
        <div className="flex items-center space-x-6">
          <button className="flex items-center text-sm font-medium text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Dashboard
          </button>
          
          <div className="flex items-center space-x-2 border-l border-gray-700 pl-6">
            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center">
              <Satellite className="w-5 h-5 text-emerald-400" />
            </div>
            <span className="font-bold text-lg tracking-wide text-white">
              SatQuery <span className="text-emerald-400">AI</span>
            </span>
          </div>
        </div>

        {/* Center: Title & Badge */}
        <div className="flex items-center space-x-4 absolute left-1/2 transform -translate-x-1/2">
          <span className="font-semibold text-gray-200">
            Sentinel-2 Multispectral Scene #8492
          </span>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Live Workspace</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center space-x-3">
          <button className="flex items-center px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800 rounded-md transition-colors border border-gray-700">
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          <button className="flex items-center px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-800 rounded-md transition-colors border border-gray-700">
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </button>
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <LeftSidebar />
        
        {/* Center Image Viewer */}
        <div className="flex-1 flex items-center justify-center relative border-x border-gray-800/60 bg-[#05080a]">
          <ImageViewer imageSrc={activeImage} setImageSrc={setActiveImage} />
        </div>

        {/* Right Chat Panel */}
        <div className="w-[400px] flex-shrink-0 bg-[#0a0e14]">
          <ChatPanel />
        </div>
      </div>
    </main>
  );
}
