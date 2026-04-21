/**
 * Cesium Canvas Component (Detailed Implementation)
 * Renders 3D terrain with flood propagation animation
 */

'use client';

import { useEffect } from 'react';
import { SimulationResponse } from '@/types/floodguard';

declare global {
  var Cesium: any;
}

interface CesiumCanvasProps {
  simulation: SimulationResponse;
  currentFrameIndex: number;
  containerRef: React.RefObject<HTMLDivElement>;
}

export default function CesiumCanvas({
  simulation,
  currentFrameIndex,
  containerRef,
}: CesiumCanvasProps) {
  useEffect(() => {
    let viewer: any;

    // Lazy load Cesium script to avoid bundle bloat
    const loadCesium = async () => {
      // In production, load from CDN:
      // https://cesium.com/downloads/cesiumjs/releases/1.108.0/Build/Cesium.js
      // and CSS: https://cesium.com/downloads/cesiumjs/releases/1.108.0/Build/Cesium.css

      if (!containerRef.current || typeof window === 'undefined') return;

      try {
        // For development, assume Cesium loaded globally via script tag
        // In package.json, cesium is listed as dependency but not bundled

        const Cesium = (window as any).Cesium;
        if (!Cesium) {
          console.error('Cesium not loaded');
          return;
        }

        // Initialize Cesium viewer
        viewer = new Cesium.Viewer(containerRef.current, {
          terrainProvider: Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(
            'https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/ImageServer',
          ),
          imageryProvider: new Cesium.ArcGisMapServerImageryProvider({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
          }),
          // Dark theme
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: false,
          timeline: false,
          animation: false,
          fullscreenButton: false,
        });

        // Set to Kenya location
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(37.9, -1.0, 500000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
          },
          duration: 0.5,
        });

        // Load current frame data
        const frame = simulation.frames[currentFrameIndex];
        if (frame && frame.flood_extent_geojson) {
          // Add flood extent polygon
          Cesium.GeoJsonDataSource.load(frame.flood_extent_geojson, {
            stroke: Cesium.Color.fromCssColorString('#EF4444'),
            fill: Cesium.Color.fromCssColorString('#EF444444'),
            strokeWidth: 2,
          }).then((dataSource: any) => {
            viewer.dataSources.add(dataSource);
          });
        }

        // Add risk node markers with colour coding
        frame?.nodes.forEach((node: any) => {
          const colour =
            node.risk_score < 0.33
              ? Cesium.Color.GREEN
              : node.risk_score < 0.66
              ? Cesium.Color.YELLOW
              : node.risk_score < 0.85
              ? Cesium.Color.RED
              : Cesium.Color.DARKRED;

          viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(node.lng, node.lat),
            point: {
              pixelSize: 8,
              color: colour,
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 2,
            },
            label: {
              text: `${(node.risk_score * 100).toFixed(0)}%`,
              font: '12px monospace',
              horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
              verticalOrigin: Cesium.VerticalOrigin.TOP,
              pixelOffset: new Cesium.Cartesian2(0, 12),
              backgroundColor: Cesium.Color.BLACK.withAlpha(0.7),
              backgroundPadding: new Cesium.Cartesian2(4, 2),
            },
          });
        });

        // Add weakness point markers (pulsing red)
        simulation.weakness_points.forEach((point: any) => {
          viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(point.lng, point.lat),
            ellipse: {
              semiMinorAxis: 50,
              semiMajorAxis: 50,
              material: Cesium.Color.RED.withAlpha(0.3),
              outline: true,
              outlineColor: Cesium.Color.RED,
            },
          });
        });

      } catch (error) {
        console.error('Cesium initialization failed:', error);
      }
    };

    loadCesium();

    return () => {
      if (viewer && !viewer.isDestroyed?.()) {
        viewer.destroy();
      }
    };
  }, [simulation, currentFrameIndex, containerRef]);

  return (
    <div
      className="w-full h-full rounded-lg overflow-hidden"
      style={{ background: '#1a1a1a' }}
    />
  );
}
