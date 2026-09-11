"use client";

import { useState, useCallback, useRef } from "react";
import { uploadImage } from "@/lib/api";
import { UploadCloud, Image as ImageIcon, CheckCircle } from "lucide-react";

interface ImageUploadSlotProps {
  label: string;
  onUploadSuccess: (imageId: string, metadata?: any) => void;
  selectedImageId?: string | null;
  sensorHint?: string;
}

export default function ImageUploadSlot({ label, onUploadSuccess, selectedImageId, sensorHint }: ImageUploadSlotProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setIsUploading(true);
    
    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target?.result as string);
    reader.readAsDataURL(file);

    try {
      const response = await uploadImage(file, sensorHint);
      onUploadSuccess(response.id, response);
    } catch (err) {
      console.error("Upload failed", err);
      setPreviewUrl(null); // Reset on error
    } finally {
      setIsUploading(false);
    }
  };

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="flex flex-col space-y-2 w-full">
      <div className="flex items-center justify-between text-sm font-semibold text-gray-300 px-1">
        <span>{label}</span>
        {selectedImageId && <CheckCircle className="w-4 h-4 text-emerald-500" />}
      </div>
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`relative flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all overflow-hidden bg-gray-900/50 min-h-[160px]
          ${isDragging ? "border-indigo-500 bg-indigo-500/10" : "border-gray-700 hover:border-gray-500 hover:bg-gray-800/80"}
          ${selectedImageId ? "border-emerald-500/50" : ""}
        `}
      >
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept="image/*,.tif,.tiff"
          onChange={onFileSelect}
        />
        
        {previewUrl ? (
          <div className="absolute inset-0 w-full h-full">
            <img src={previewUrl} alt="Preview" className="w-full h-full object-cover opacity-60" />
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <span className="text-white text-xs font-semibold bg-black/60 px-3 py-1.5 rounded-full">Replace Image</span>
            </div>
            {isUploading && (
              <div className="absolute inset-0 bg-gray-900/80 flex flex-col items-center justify-center z-10 backdrop-blur-sm">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3"></div>
                <span className="text-sm font-medium text-indigo-400">Uploading...</span>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center text-center space-y-3 z-10 relative">
            <div className="p-3 bg-gray-800 rounded-full shadow-inner">
              <UploadCloud className="w-6 h-6 text-gray-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-300">
                <span className="text-indigo-400">Click to browse</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500 mt-1">GeoTIFF, PNG, JPG up to 50MB</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
