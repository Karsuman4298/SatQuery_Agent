"use client";

import { useState } from "react";
import { Satellite } from "lucide-react";
import ImageViewer from "@/components/ImageViewer";
import ChatPanel from "@/components/ChatPanel";
import LeftPanel from "@/components/LeftPanel";
import TemporalView from "@/components/TemporalView";
import FusionView from "@/components/FusionView";
import { createRegion } from "@/lib/api";
import { ImageMetadata } from "@/lib/types";
import ResizableLayout from "@/components/ResizableLayout";

export default function Home() {
  const [images, setImages] = useState<ImageMetadata[]>([]);
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);
  const [activeRegionName, setActiveRegionName] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [regionRefreshCount, setRegionRefreshCount] = useState(0);
  const [changeMaskUrl, setChangeMaskUrl] = useState<string | null>(null);

  const handleUploadSuccess = (metadata: ImageMetadata) => {
    setImages(prev => [...prev, metadata]);
  };

  const handleRegionDrawn = async (bounds: any) => {
    if (images.length === 0) return;
    try {
      const name = `Region ${String.fromCharCode(65 + (regionRefreshCount % 26))}`;
      const newRegion = await createRegion(images[0].id, name, bounds);
      setActiveRegionId(newRegion.id);
      setActiveRegionName(newRegion.name);
      setRegionRefreshCount(c => c + 1);
    } catch (err) {
      console.error("Failed to save region", err);
    }
  };

  const handleRegionSelect = (id: string | null, name: string | null) => {
    setActiveRegionId(id);
    setActiveRegionName(name);
  };

  // Auto-detect view mode based on images uploaded
  const isTemporal = images.length >= 2 && images[0].sensor === images[1].sensor;
  const isFusion = images.length >= 2 && images[0].sensor !== images[1].sensor;

  const leftPanel = (
    <div className="h-full bg-gray-900 border-r border-gray-800">
      <LeftPanel 
        images={images}
        onUploadSuccess={handleUploadSuccess}
        activeRegionId={activeRegionId}
        onRegionSelect={handleRegionSelect}
        regionRefreshCount={regionRefreshCount}
      />
    </div>
  );

  const centerPanel = (
    <div className="h-full relative bg-black p-4 flex flex-col items-center justify-center">
      <div className="w-full h-full relative rounded-xl border border-gray-800 bg-gray-950 overflow-hidden shadow-2xl">
        {images.length > 0 ? (
          <>
            <ImageViewer 
              imageId={images[0].id}
              imageMeta={images[0]} 
              onRegionDrawn={handleRegionDrawn}
              evidenceOverlay={evidence}
              changeMaskUrl={changeMaskUrl}
            />
            {isTemporal && (
              <TemporalView 
                beforeImageId={images[0].id} 
                afterImageId={images[1].id} 
                onChangeMaskReceived={setChangeMaskUrl}
              />
            )}
            {isFusion && (
              <FusionView opticalId={images[0].id} sarId={images[1].id} />
            )}
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
            <div className="flex flex-col items-center">
              <Satellite className="w-12 h-12 mb-4 opacity-20" />
              Upload an image in the left panel to begin analysis.
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const rightPanel = (
    <div className="h-full bg-gray-900 border-l border-gray-800 shadow-xl">
      <ChatPanel 
        imageId={images.length > 0 ? images[0].id : null}
        activeRegionId={activeRegionId}
        activeRegionName={activeRegionName}
        onEvidenceReceived={setEvidence}
      />
    </div>
  );

  return (
    <main className="flex flex-col h-screen w-full bg-black text-white font-sans overflow-hidden">
      {/* Header */}
      <div className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 flex-shrink-0 z-10">
        <div className="flex items-center space-x-2">
          <Satellite className="w-5 h-5 text-emerald-400" />
          <span className="font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">
            SatQuery IDE
          </span>
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 overflow-hidden h-[calc(100vh-3rem)]">
        <ResizableLayout 
          leftPanel={leftPanel}
          centerPanel={centerPanel}
          rightPanel={rightPanel}
          defaultLeftWidth={320}
          defaultRightWidth={400}
        />
      </div>
    </main>
  );
}
