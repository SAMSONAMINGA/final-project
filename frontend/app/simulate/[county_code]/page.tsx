/**
 * Simulation Page — 3D Cesium Terrain Viewer
 * Displays flood propagation animation with timeline controls
 */

'use client';

import { useParams } from 'next/navigation';
import { useTriggerSimulation } from '@/hooks/useSimulation';
import { useEffect } from 'react';
import { CesiumViewer } from '@/components/simulation/CesiumViewer';
import { CardSkeleton } from '@/components/common/Skeleton';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function SimulatePage() {
  const params = useParams();
  const countyCode = params.county_code as string;
  const triggerSim = useTriggerSimulation();

  useEffect(() => {
    // Auto-trigger simulation on page load
    if (countyCode) {
      triggerSim.mutate(countyCode);
    }
  }, [countyCode, triggerSim]);

  return (
    <ErrorBoundary>
      <div className="h-screen w-screen flex flex-col bg-gray-900">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
          <div>
            <Link
              href="/"
              className="flex items-center gap-2 text-savanna-gold hover:text-savanna-dark transition mb-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Map
            </Link>
            <h1 className="text-2xl font-bold text-white">
              Flood Simulation — {countyCode}
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              3D terrain viewer with animated flood propagation (3-hour forecast)
            </p>
          </div>
        </div>

        {/* 3D Viewer */}
        <div className="flex-1 overflow-hidden">
          {triggerSim.isPending ? (
            <div className="w-full h-full flex items-center justify-center bg-gray-900">
              <CardSkeleton />
            </div>
          ) : triggerSim.data ? (
            <CesiumViewer simulation={triggerSim.data} />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-900">
              <div className="text-center space-y-4">
                <p className="text-gray-400">Failed to load simulation data</p>
                <button
                  onClick={() => triggerSim.mutate(countyCode)}
                  className="px-4 py-2 bg-savanna-gold text-black font-semibold rounded hover:bg-savanna-dark transition"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}
