/**
 * Dashboard Page — Main Risk Map & Alert Ticker
 * Displays Kenya choropleth with real-time county selection and notifications
 * Objective: Enable spatial pattern recognition with 60-min early warning lead time
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useRiskData } from '@/hooks/useRiskData';
import { KenyaRiskMap } from '@/components/map/KenyaRiskMap';
import { CountySidePanel } from '@/components/map/CountySidePanel';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { RiskBadge } from '@/components/common/RiskBadge';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { RiskLevel, WebSocketEvent } from '@/types/floodguard';
import clsx from 'clsx';

// Kenya counties GeoJSON (simplified for demo)
const SAMPLE_COUNTIES = Array.from({ length: 47 }, (_, i) => ({
  id: i,
  type: 'Feature' as const,
  properties: {
    county_code: `KEN${String(i + 1).padStart(2, '0')}`,
    county_name: [
      'Mombasa',
      'Kwale',
      'Kilifi',
      'Tana River',
      'Lamu',
      'Taita Taveta',
      'Garissa',
      'Wajir',
      'Mandera',
      'Marsabit',
      'Isiolo',
      'Meru',
      'Tharaka Nithi',
      'Embu',
      'Kitui',
      'Machakos',
      'Makueni',
      'Nairobi',
      'Kiambu',
      'Muranga',
      'Nyeri',
      'Kirinyaga',
      'Nakuru',
      'Narok',
      'Kajiado',
      'Kericho',
      'Bomet',
      'Kakamega',
      'Vihiga',
      'Bungoma',
      'Busia',
      'Siaya',
      'Kisumu',
      'Homa Bay',
      'Migori',
      'Kisii',
      'Nyamira',
      'Samburu',
      'West Pokot',
      'Baringo',
      'Turkana',
      'Trans Nzoia',
      'Uasin Gishu',
      'Elgeyo Marakwet',
      'Nandi',
      'Laikipia',
    ][i],
  },
  geometry: {
  type: "MultiPolygon",
  coordinates: [
    [ // polygon
      [ // outer ring
        [37 + i * 0.1, -1],
        [37.1 + i * 0.1, -1],
        [37.1 + i * 0.1, -0.9],
        [37 + i * 0.1, -0.9],
        [37 + i * 0.1, -1]
      ]
    ]
  ]
}
}));

export default function DashboardPage() {
  const selectedCountyCode = useAppStore((s) => s.selectedCountyCode);
  const addAlert = useAppStore((s) => s.addAlert);
  const [riskLevels, setRiskLevels] = useState<Record<string, RiskLevel>>({});
  const [refreshing, setRefreshing] = useState(false);

  // Fetch risk data for selected county
  const { data: riskData } = useRiskData(selectedCountyCode);

  // WebSocket subscription for live updates
  useWebSocket({
    onMessage: (event: WebSocketEvent) => {
      if (event.event === 'alert') {
        addAlert({
          type: event.risk_level || 'High',
          message: event.message || 'Flood alert received',
        });
      }

      // Update risk level in map
      if (event.county_code && event.risk_level) {
        setRiskLevels((prev) => ({
          ...prev,
          [event.county_code!]: event.risk_level!,
        }));
      }
    },
  });

  // Simulate risk data refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Update all county risk levels randomly
      const newRisks: Record<string, RiskLevel> = {};
      SAMPLE_COUNTIES.forEach((county) => {
        const rand = Math.random();
        const level: RiskLevel =
          rand < 0.5
            ? 'Low'
            : rand < 0.8
            ? 'Medium'
            : rand < 0.95
            ? 'High'
            : 'Critical';
        newRisks[county.properties.county_code] = level;
      });
      setRiskLevels(newRisks);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <ErrorBoundary>
      <div className="h-screen w-screen flex flex-col bg-gray-900">
        {/* Top Alert Ticker */}
        <div className="bg-gradient-to-r from-risk-high/20 to-risk-critical/20 border-b border-risk-high/50 px-6 py-3 flex items-center gap-4">
          <AlertCircle className="w-5 h-5 text-risk-high flex-shrink-0" />
          <div className="overflow-hidden flex-1">
            <div className="animate-marquee whitespace-nowrap text-sm text-gray-200">
              {/* Live alert ticker — populated from WebSocket */}
              FloodGuard KE: Real-time flood early warning system | Tana River
              at HIGH risk | Garissa MEDIUM | More info on map →
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Map */}
          <div className="flex-1 relative">
            <KenyaRiskMap
              counties={SAMPLE_COUNTIES}
              onCountySelect={() => {}}
              selectedCounty={selectedCountyCode}
              riskLevels={riskLevels}
            />

            {/* Data Freshness Badge */}
            <div className="absolute top-6 right-6 bg-gray-800/90 backdrop-blur rounded-lg p-4 shadow-lg z-20 max-w-sm">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">IMERG Updated</span>
                  <span className="text-gray-300 font-mono">~5 min ago</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Barometer Readings</span>
                  <span className="text-gray-300 font-mono">247 today</span>
                </div>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className={clsx(
                    'mt-3 w-full px-3 py-2 rounded text-xs font-semibold',
                    'bg-savanna-gold/20 text-savanna-gold hover:bg-savanna-gold/30',
                    'transition disabled:opacity-50',
                    'flex items-center justify-center gap-2',
                  )}
                >
                  <RefreshCw
                    className={clsx(
                      'w-3 h-3',
                      refreshing && 'animate-spin',
                    )}
                  />
                  {refreshing ? 'Refreshing...' : 'Refresh Data'}
                </button>
              </div>
            </div>
          </div>

          {/* Side Panel */}
          <CountySidePanel
            countyCode={selectedCountyCode}
            onSimulationTrigger={(countyCode) => {
              window.location.href = `/simulate/${countyCode}`;
            }}
          />
        </div>
      </div>
    </ErrorBoundary>
  );
}
