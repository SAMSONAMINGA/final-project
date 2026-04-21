/**
 * Cesium 3D Viewer Component
 * Displays flood simulation with 3D terrain, animated flood propagation, and node markers
 * Objective: Enable spatial interpretation of flood extent & progression (60-min lead time)
 */

'use client';

import { useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { SimulationResponse } from '@/types/floodguard';
import { CardSkeleton } from '@/components/common/Skeleton';

interface CesiumViewerProps {
  simulation: SimulationResponse;
  onFrameChange?: (frameIndex: number) => void;
}

/**
 * Dynamically import Cesium to avoid SSR issues
 * Cesium requires browser window object & canvas support
 */
const CesiumComponent = dynamic(
  () => import('@/components/simulation/CesiumCanvas'),
  {
    loading: () => <CardSkeleton />,
    ssr: false,
  },
);

export function CesiumViewer({
  simulation,
  onFrameChange,
}: CesiumViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);

  const handleFrameChange = (index: number) => {
    setCurrentFrameIndex(index);
    onFrameChange?.(index);
  };

  return (
    <div className="relative w-full h-full bg-gray-900" ref={containerRef}>
      {/* 3D Canvas */}
      <CesiumComponent
        simulation={simulation}
        currentFrameIndex={currentFrameIndex}
        containerRef={containerRef}
      />

      {/* Timeline Controls (overlaid bottom) */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6">
        <div className="flex items-center gap-4">
          {/* Frame counter */}
          <div className="text-sm text-gray-300">
            Frame {currentFrameIndex + 1} / {simulation.frames.length}
            {' '}
            ({simulation.frames[currentFrameIndex]?.t_minutes || 0} min)
          </div>

          {/* Timeline slider */}
          <input
            type="range"
            min="0"
            max={simulation.frames.length - 1}
            value={currentFrameIndex}
            onChange={(e) => handleFrameChange(parseInt(e.target.value))}
            className="flex-1 h-2 bg-gray-700 rounded cursor-pointer"
            aria-label="Simulation timeline scrubber"
          />

          {/* Time label */}
          <div className="text-sm text-gray-300 min-w-20 text-right">
            {simulation.frames[currentFrameIndex]?.t_minutes || 0} min
          </div>
        </div>
      </div>

      {/* Weakness points indicator */}
      <div className="absolute top-6 right-6 bg-gray-800/90 backdrop-blur rounded-lg p-4 max-w-xs z-20">
        <h4 className="text-sm font-semibold text-white mb-2">
          Weakness Points ({simulation.weakness_points.length})
        </h4>
        <div className="space-y-1 max-h-40 overflow-y-auto text-xs">
          {simulation.weakness_points.map((point) => (
            <div
              key={point.node_id}
              className="text-gray-300 flex justify-between"
            >
              <span>{point.node_id}</span>
              <span className="text-risk-high font-semibold">
                {(point.risk_score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
