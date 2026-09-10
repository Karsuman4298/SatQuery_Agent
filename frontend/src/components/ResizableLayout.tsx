"use client";

import { useState, useRef, useEffect, ReactNode } from "react";

interface ResizableLayoutProps {
  leftPanel: ReactNode;
  centerPanel: ReactNode;
  rightPanel: ReactNode;
  defaultLeftWidth?: number;
  defaultRightWidth?: number;
}

export default function ResizableLayout({
  leftPanel,
  centerPanel,
  rightPanel,
  defaultLeftWidth = 300,
  defaultRightWidth = 400,
}: ResizableLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [rightWidth, setRightWidth] = useState(defaultRightWidth);
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();

      if (isDraggingLeft) {
        const newWidth = e.clientX - containerRect.left;
        setLeftWidth(Math.max(200, Math.min(newWidth, containerRect.width / 2.5)));
      }

      if (isDraggingRight) {
        const newWidth = containerRect.right - e.clientX;
        setRightWidth(Math.max(250, Math.min(newWidth, containerRect.width / 2.5)));
      }
    };

    const handleMouseUp = () => {
      setIsDraggingLeft(false);
      setIsDraggingRight(false);
    };

    if (isDraggingLeft || isDraggingRight) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
    } else {
      document.body.style.cursor = "default";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "default";
    };
  }, [isDraggingLeft, isDraggingRight]);

  return (
    <div ref={containerRef} className="flex h-full w-full overflow-hidden">
      {/* Left Panel */}
      <div style={{ width: leftWidth }} className="flex-shrink-0 h-full">
        {leftPanel}
      </div>

      {/* Left Resizer */}
      <div
        className="w-1 bg-gray-800 hover:bg-emerald-500 cursor-col-resize flex-shrink-0 z-50 transition-colors"
        onMouseDown={() => setIsDraggingLeft(true)}
      />

      {/* Center Panel */}
      <div className="flex-1 h-full min-w-0">
        {centerPanel}
      </div>

      {/* Right Resizer */}
      <div
        className="w-1 bg-gray-800 hover:bg-emerald-500 cursor-col-resize flex-shrink-0 z-50 transition-colors"
        onMouseDown={() => setIsDraggingRight(true)}
      />

      {/* Right Panel */}
      <div style={{ width: rightWidth }} className="flex-shrink-0 h-full">
        {rightPanel}
      </div>
    </div>
  );
}
