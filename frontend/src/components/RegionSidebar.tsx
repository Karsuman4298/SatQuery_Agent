"use client";

import { useEffect, useState } from "react";
import { listRegions } from "@/lib/api";
import { MapPin, Maximize } from "lucide-react";

interface RegionSidebarProps {
  imageId: string | null;
  imageMeta?: any | null;
  activeRegionId: string | null;
  onRegionSelect: (id: string | null, name: string | null) => void;
  refreshTrigger: number;
}

export default function RegionSidebar({ imageId, imageMeta, activeRegionId, onRegionSelect, refreshTrigger }: RegionSidebarProps) {
  const [regions, setRegions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    if (!imageId) {
      setRegions([]);
      return;
    }

    const fetchRegions = async () => {
      setIsLoading(true);
      try {
        const data = await listRegions(imageId);
        setRegions(data);
      } catch (e) {
        console.error("Failed to list regions", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRegions();
  }, [imageId, refreshTrigger]);

  const calculateMockArea = (bounds: any) => {
    if (!bounds) return "0.00";
    const w = bounds.x_max - bounds.x_min;
    const h = bounds.y_max - bounds.y_min;
    // Rough estimation: assuming each pixel is roughly 10 meters resolution for a mock image
    const areaSqMeters = w * 10 * h * 10;
    const areaSqKm = areaSqMeters / 1_000_000;
    return areaSqKm.toFixed(2);
  };

  const calculateGeoCoords = (bounds: any) => {
    if (!bounds || !imageMeta) return null;
    let minLon = 73.85; let minLat = 18.52;
    let maxLon = 73.95; let maxLat = 18.62;

    if (imageMeta.bounds?.coordinates?.[0]) {
      const coords = imageMeta.bounds.coordinates[0];
      minLon = coords[0][0]; minLat = coords[0][1];
      maxLon = coords[2][0]; maxLat = coords[2][1];
    }

    // This is a rough estimation of the cropped bounding box lat/lon
    // Assuming image width is around 1024 as fallback if not in meta
    const imgW = imageMeta.width_px || 1024;
    const imgH = imageMeta.height_px || 1024;

    const cropMinLon = minLon + (maxLon - minLon) * (bounds.x_min / imgW);
    const cropMaxLon = minLon + (maxLon - minLon) * (bounds.x_max / imgW);
    const cropMaxLat = maxLat - (maxLat - minLat) * (bounds.y_min / imgH);
    const cropMinLat = maxLat - (maxLat - minLat) * (bounds.y_max / imgH);

    return { cropMinLon, cropMaxLon, cropMinLat, cropMaxLat };
  };

  return (
    <div className="w-full flex flex-col h-full">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Regions</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        <button
          onClick={() => onRegionSelect(null, null)}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors mb-1 ${
            activeRegionId === null 
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30" 
              : "text-gray-300 hover:bg-gray-800"
          }`}
        >
          Full Image
        </button>

        {isLoading ? (
          <div className="px-3 py-2 text-sm text-gray-500">Loading...</div>
        ) : (
          regions.map((region) => {
            const isActive = activeRegionId === region.id;
            const geo = calculateGeoCoords(region.pixel_bounds);

            return (
              <div key={region.id} className="mb-2">
                <button
                  onClick={() => onRegionSelect(region.id, region.name)}
                  className={`w-full flex items-center justify-between text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive 
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-b-none" 
                      : "text-gray-300 hover:bg-gray-800"
                  }`}
                >
                  <span className="truncate pr-2 font-medium">{region.name}</span>
                  {isActive && <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />}
                </button>

                {isActive && (
                  <div className="bg-gray-950 border border-t-0 border-emerald-500/30 rounded-b-lg p-3 text-xs flex flex-col gap-3">
                    {/* Thumbnail Crop using object-position hack */}
                    {region.pixel_bounds && (
                      <div className="relative w-full h-24 overflow-hidden rounded border border-gray-800 bg-black group">
                        <img 
                          src={`${API_BASE_URL}/images/${imageId}/tile`}
                          className="absolute max-w-none opacity-80 group-hover:opacity-100 transition-opacity"
                          style={{
                            left: `-${region.pixel_bounds.x_min}px`,
                            top: `-${region.pixel_bounds.y_min}px`,
                            width: `${imageMeta?.width_px || 1024}px`,
                            height: `${imageMeta?.height_px || 1024}px`
                          }}
                          alt="Region Crop"
                        />
                        <div className="absolute inset-0 ring-1 ring-inset ring-emerald-500/50 pointer-events-none" />
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-2 text-gray-400">
                      <div className="flex flex-col bg-gray-900 p-2 rounded">
                        <span className="flex items-center gap-1 text-[10px] uppercase text-gray-500 mb-0.5"><Maximize className="w-3 h-3"/> Area</span>
                        <span className="font-mono text-gray-200">{calculateMockArea(region.pixel_bounds)} sq km</span>
                      </div>
                      <div className="flex flex-col bg-gray-900 p-2 rounded">
                        <span className="flex items-center gap-1 text-[10px] uppercase text-gray-500 mb-0.5"><MapPin className="w-3 h-3"/> Center Lat</span>
                        <span className="font-mono text-emerald-400">{geo ? ((geo.cropMinLat + geo.cropMaxLat) / 2).toFixed(4) : "N/A"}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
        
        {regions.length === 0 && !isLoading && imageId && (
          <div className="px-3 py-4 text-xs text-gray-500 italic text-center">
            Draw a rectangle on the image to create a region.
          </div>
        )}
      </div>
    </div>
  );
}
