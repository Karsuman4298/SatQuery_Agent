import { Layers, Info, Map } from "lucide-react";

export default function LeftSidebar() {
  return (
    <div className="w-[300px] flex-shrink-0 bg-[#0a0e14] h-full flex flex-col border-r border-gray-800/60 p-5 overflow-y-auto custom-scrollbar">
      
      {/* Spectral Channels */}
      <div className="mb-8">
        <div className="flex items-center space-x-2 text-gray-400 font-semibold text-xs tracking-wider mb-4 uppercase">
          <Layers className="w-4 h-4" />
          <span>Spectral Channels</span>
        </div>
        <div className="space-y-2">
          {/* Active Item */}
          <button className="w-full flex items-center justify-between p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <span className="font-medium text-sm text-left">True Color (RGB)</span>
          </button>
          {/* Inactive Items */}
          <button className="w-full flex items-center justify-between p-3 rounded-lg border border-gray-800 hover:border-gray-700 bg-[#0f141a] text-gray-400 hover:text-gray-300 transition-colors">
            <span className="font-medium text-sm text-left">NDVI Vegetation</span>
          </button>
          <button className="w-full flex items-center justify-between p-3 rounded-lg border border-gray-800 hover:border-gray-700 bg-[#0f141a] text-gray-400 hover:text-gray-300 transition-colors">
            <span className="font-medium text-sm text-left">False Color NIR</span>
          </button>
          <button className="w-full flex items-center justify-between p-3 rounded-lg border border-gray-800 hover:border-gray-700 bg-[#0f141a] text-gray-400 hover:text-gray-300 transition-colors">
            <span className="font-medium text-sm text-left">SWIR Moisture</span>
          </button>
        </div>
      </div>

      {/* Detected Regions */}
      <div className="mb-8">
        <div className="flex items-center space-x-2 text-gray-400 font-semibold text-xs tracking-wider mb-4 uppercase">
          <Map className="w-4 h-4" />
          <span>Detected Regions</span>
        </div>
        <div className="space-y-2">
          {/* Region Alpha */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-emerald-500/30 bg-[#0a1815]">
            <div className="flex flex-col">
              <span className="font-semibold text-emerald-400 text-sm">Region Alpha</span>
              <span className="text-gray-500 text-xs mt-0.5">Canopy Density</span>
            </div>
            <span className="text-emerald-400 font-bold">96%</span>
          </div>
          {/* Region Beta */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-[#0f141a]">
            <div className="flex flex-col">
              <span className="font-semibold text-gray-200 text-sm">Region Beta</span>
              <span className="text-gray-500 text-xs mt-0.5">Hydrological Flow</span>
            </div>
            <span className="text-emerald-400 font-bold">91%</span>
          </div>
          {/* Sector Gamma */}
          <div className="flex items-center justify-between p-3 rounded-lg border border-gray-800 bg-[#0f141a]">
            <div className="flex flex-col">
              <span className="font-semibold text-gray-200 text-sm">Sector Gamma</span>
              <span className="text-gray-500 text-xs mt-0.5">Urban Boundary</span>
            </div>
            <span className="text-emerald-400 font-bold">88%</span>
          </div>
        </div>
      </div>

      {/* Observation Summary */}
      <div className="mt-auto">
        <div className="flex items-center space-x-2 text-gray-400 font-semibold text-xs tracking-wider mb-4 uppercase">
          <Info className="w-4 h-4" />
          <span>Observation Summary</span>
        </div>
        <div className="rounded-lg border border-gray-800 bg-[#0f141a] p-4 text-sm divide-y divide-gray-800/60">
          <div className="flex justify-between py-2">
            <span className="text-gray-500">Spatial Resolution</span>
            <span className="text-gray-300 font-medium">10m / px</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-gray-500">Sensor Modality</span>
            <div className="text-right">
              <div className="text-gray-300 font-medium">Optical &</div>
              <div className="text-gray-300 font-medium">Multispectral</div>
            </div>
          </div>
          <div className="flex justify-between pt-2">
            <span className="text-gray-500">Cloud Cover</span>
            <span className="text-gray-300 font-medium">&lt; 0.4%</span>
          </div>
        </div>
      </div>

    </div>
  );
}
