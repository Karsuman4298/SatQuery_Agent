"use client";

import { useState, useCallback } from "react";
import { uploadImage } from "@/lib/api";
import { UploadCloud, Image as ImageIcon, Map, Layers } from "lucide-react";
import RegionSidebar from "./RegionSidebar";

interface LeftPanelProps {
  images: any[];
  onUploadSuccess: (metadata: any) => void;
  activeRegionId: string | null;
  onRegionSelect: (id: string | null, name: string | null) => void;
  regionRefreshCount: number;
}

export default function LeftPanel({
  images,
  onUploadSuccess,
  activeRegionId,
  onRegionSelect,
  regionRefreshCount,
}: LeftPanelProps) {
  const [isUploading, setIsUploading] = useState(false);

  const processFile = async (file: File) => {
    setIsUploading(true);
    try {
      const metadata = await uploadImage(file);
      onUploadSuccess(metadata);
    } catch (err: any) {
      console.error(err.message || "Failed to upload image.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 border-r border-gray-800 text-sm overflow-hidden">
      <div className="p-4 border-b border-gray-800 flex-shrink-0">
        <h2 className="font-semibold text-white mb-3 uppercase text-xs tracking-wider text-gray-400">Context</h2>
        
        {/* Upload Zone */}
        <label className={`
          flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-4 cursor-pointer transition-colors
          ${isUploading ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-gray-700 hover:border-gray-500 hover:bg-gray-800'}
        `}>
          <input
            type="file"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) processFile(e.target.files[0]);
              e.target.value = '';
            }}
            accept=".tif,.tiff,.png,.jpg,.jpeg"
            disabled={isUploading}
          />
          {isUploading ? (
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          ) : (
            <>
              <UploadCloud className="w-6 h-6 text-gray-400 mb-2" />
              <span className="text-gray-300 text-xs">Click to upload image</span>
            </>
          )}
        </label>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Uploaded Images List */}
        {images.length > 0 && (
          <div className="p-4 border-b border-gray-800">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Workspace</h3>
            <div className="space-y-2">
              {images.map((img, i) => (
                <div key={img.id} className="flex items-center space-x-2 bg-gray-800 p-2 rounded text-xs text-gray-300">
                  {img.sensor === 'SAR' ? <Layers className="w-4 h-4 text-indigo-400" /> : <ImageIcon className="w-4 h-4 text-emerald-400" />}
                  <span className="truncate flex-1">{img.filename || `Image ${i + 1}`}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Region Selector */}
        <div className="flex-1">
          <RegionSidebar 
            imageId={images.length > 0 ? images[0].id : null} 
            imageMeta={images.length > 0 ? images[0] : null}
            activeRegionId={activeRegionId} 
            onRegionSelect={onRegionSelect}
            refreshTrigger={regionRefreshCount}
          />
        </div>
      </div>
    </div>
  );
}
