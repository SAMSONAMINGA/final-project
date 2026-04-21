/**
 * Kenya Risk Map Component
 * Full-screen Mapbox GL JS choropleth map with 47 counties
 * Objective: Enable spatial pattern recognition for decision makers (60-min lead time)
 * Accessibility: WCAG 2.1 AA keyboard navigation & screen reader support
 */

'use client';

import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '@/lib/store';
import { RiskLevel } from '@/types/floodguard';

export interface CountyFeature {
  id: string | number;
  type: 'Feature';
  properties: {
    county_code: string;
    county_name: string;
    risk_level?: RiskLevel;
    risk_score?: number;
  };
  geometry: GeoJSON.Geometry;
}

interface KenyaRiskMapProps {
  counties: CountyFeature[];
  onCountySelect: (countyCode: string) => void;
  selectedCounty?: string | null;
  riskLevels?: Record<string, RiskLevel>;
}

// Accessible colour mapping with WCAG AA contrast
const RISK_COLOURS: Record<RiskLevel | 'unknown', string> = {
  Low: '#10B981', // Emerald
  Medium: '#F59E0B', // Amber
  High: '#EF4444', // Red
  Critical: '#7F1D1D', // Dark red
  unknown: '#4B5563', // Gray
};

export function KenyaRiskMap({
  counties,
  onCountySelect,
  selectedCounty,
  riskLevels,
}: KenyaRiskMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const setSelectedCountyCode = useAppStore((s) => s.setSelectedCountyCode);

  // Initialize Mapbox map
  useEffect(() => {
    if (!mapContainer.current) return;

    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [37.9, -1.0], // Kenya centroid
      zoom: 5.5,
      pitch: 0,
      bearing: 0,
      // Accessibility: enable keyboard navigation (arrow keys, +/-, etc)
      keyboard: true,
      doubleClickZoom: true,
    });

    map.current.on('load', () => {
      // Add counties GeoJSON source
      map.current!.addSource('counties', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: counties as GeoJSON.Feature[],
        },
      });

      // Add fill layer with dynamic colouring based on risk
      map.current!.addLayer({
        id: 'counties-fill',
        type: 'fill',
        source: 'counties',
        paint: {
          'fill-color': [
            'case',
            // If risk_level set, use appropriate colour
            ['has', 'risk_level', ['feature-state', 'data']],
            [
              'match',
              ['get', 'risk_level', ['feature-state', 'data']],
              'Low',
              RISK_COLOURS.Low,
              'Medium',
              RISK_COLOURS.Medium,
              'High',
              RISK_COLOURS.High,
              'Critical',
              RISK_COLOURS.Critical,
              RISK_COLOURS.unknown,
            ],
            RISK_COLOURS.unknown,
          ],
          'fill-opacity': 0.7,
        },
      });

      // Add border layer
      map.current!.addLayer({
        id: 'counties-border',
        type: 'line',
        source: 'counties',
        paint: {
          'line-color': '#ffffff',
          'line-width': 2,
          'line-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            1,
            0.5,
          ],
        },
      });

      // Add labels (county names)
      map.current!.addLayer({
        id: 'county-labels',
        type: 'symbol',
        source: 'counties',
        layout: {
          'text-field': ['get', 'county_name'],
          'text-size': 12,
          'text-max-width': 5,
          'text-letter-spacing': 0,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#000000',
          'text-halo-width': 1,
        },
      });

      // Hover effects
      let hoveredStateId: string | number | null = null;

      map.current!.on('mousemove', 'counties-fill', (e) => {
        if (e.features && e.features.length > 0) {
          if (hoveredStateId !== null) {
            map.current!.setFeatureState(
              { source: 'counties', id: hoveredStateId },
              { hover: false },
            );
          }
          const featureId = e.features[0].id;
          if (featureId === undefined) return;

          hoveredStateId = featureId;
          map.current!.setFeatureState(
            { source: 'counties', id: hoveredStateId },
            { hover: true },
          );
          map.current!.getCanvas().style.cursor = 'pointer';
        }
      });

      map.current!.on('mouseleave', 'counties-fill', () => {
        if (hoveredStateId !== null) {
          map.current!.setFeatureState(
            { source: 'counties', id: hoveredStateId },
            { hover: false },
          );
        }
        hoveredStateId = null;
        map.current!.getCanvas().style.cursor = '';
      });

      // Click to select county
      map.current!.on('click', 'counties-fill', (e) => {
        if (e.features && e.features.length > 0) {
          const countyCode = e.features[0].properties?.county_code;
          if (typeof countyCode === 'string') {
            setSelectedCountyCode(countyCode);
            onCountySelect(countyCode);
          }
        }
      });
    });

    return () => {
      map.current?.remove();
    };
  }, [counties, onCountySelect, setSelectedCountyCode]);

  // Update county feature state when risk levels change
  useEffect(() => {
    if (!map.current || !riskLevels) return;

    Object.entries(riskLevels).forEach(([countyCode, riskLevel]) => {
      // Find feature ID for county
      const feature = counties.find(
        (c) => c.properties.county_code === countyCode,
      );
      if (feature && feature.id) {
        map.current!.setFeatureState(
          { source: 'counties', id: feature.id },
          { risk_level: riskLevel },
        );
      }
    });
  }, [riskLevels, counties]);

  // Highlight selected county
  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap) return;

    currentMap.setPaintProperty(
      'counties-border',
      'line-width',
      [
        'case',
        [
          'boolean',
          [
            'feature-state',
            'selected',
            // Find which feature matches selected county
            counties.some((c) => c.properties.county_code === selectedCounty),
          ],
        ],
        4,
        2,
      ],
    );

    // Fly to selected county bounds
    if (selectedCounty) {
      const feature = counties.find(
        (c) => c.properties.county_code === selectedCounty,
      );
      if (feature && feature.geometry) {
        const bbox = calculateBbox(feature.geometry);
        if (bbox) {
          currentMap.fitBounds(bbox, { padding: 40, duration: 800 });
        }
      }
    }
  }, [selectedCounty, counties]);

  return (
    <div
      ref={mapContainer}
      className="relative w-full h-full bg-gray-900"
      role="region"
      aria-label="Kenya risk map showing 47 counties colour-coded by flood risk level"
    >
      {/* Legend */}
      <div
        className="absolute bottom-8 left-8 bg-gray-800/90 backdrop-blur rounded-lg p-4 shadow-lg z-10 max-w-xs"
        role="complementary"
        aria-label="Risk level legend"
      >
        <h3 className="text-sm font-semibold text-white mb-3">Risk Levels</h3>
        <div className="space-y-2 text-xs">
          {Object.entries(RISK_COLOURS).map(([level, colour]) => (
            <div key={level} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: colour }}
                aria-hidden="true"
              />
              <span className="text-gray-300">{level}</span>
            </div>
          ))}
        </div>
      </div>

      {/* County Info Card */}
      {selectedCounty && (
        <div
          className="absolute top-8 left-8 bg-gray-800/90 backdrop-blur rounded-lg p-4 shadow-lg z-10 max-w-sm"
          role="region"
          aria-live="polite"
          aria-label={`Selected county: ${selectedCounty}`}
        >
          <h3 className="text-lg font-semibold text-white mb-2">
            {selectedCounty}
          </h3>
          <p className="text-xs text-gray-400">Click to view risk details</p>
        </div>
      )}
    </div>
  );
}

/**
 * Calculate bounding box (bbox) from GeoJSON geometry
 * Used for fitBounds animation when county selected
 */
function calculateBbox(
  geometry: any,
): [[number, number], [number, number]] | null {
  if (!geometry || !geometry.coordinates) return null;

  let minLng = Infinity,
    minLat = Infinity,
    maxLng = -Infinity,
    maxLat = -Infinity;

  function processCoords(coords: number[] | any[]): void {
    if (typeof coords[0] === 'number') {
      // [lng, lat] pair
      minLng = Math.min(minLng, coords[0]);
      maxLng = Math.max(maxLng, coords[0]);
      minLat = Math.min(minLat, coords[1]);
      maxLat = Math.max(maxLat, coords[1]);
    } else {
      // Recursive for nested coordinate arrays
      coords.forEach(processCoords);
    }
  }

  processCoords(geometry.coordinates);

  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}
