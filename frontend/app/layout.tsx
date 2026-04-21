/**
 * Root Layout
 * NextAuth.js session provider, React Query provider, dark theme
 */

import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Provider as SessionProvider } from '@/components/auth/SessionProvider';
import { QueryProvider } from '@/components/auth/QueryProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'FloodGuard KE — Nationwide Flood Early Warning',
  description:
    'Real-time flood risk dashboard for Kenya using GATv2 ML, Extended Kalman Filter, and SHAP explainability',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Mapbox GL JS CSS */}
        <link
          href="https://api.mapbox.com/mapbox-gl-js/v3.0.1/mapbox-gl.css"
          rel="stylesheet"
        />
        {/* Cesium CSS */}
        <link
          href="https://cesium.com/downloads/cesiumjs/releases/1.108.0/Build/Cesium.css"
          rel="stylesheet"
        />
      </head>
      <body>
        <SessionProvider>
          <QueryProvider>{children}</QueryProvider>
        </SessionProvider>

        {/* Cesium JS (lazy loaded) */}
        <script src="https://cesium.com/downloads/cesiumjs/releases/1.108.0/Build/Cesium.js"></script>
      </body>
    </html>
  );
}
