# FloodGuard KE Frontend Documentation

## Overview

Production-grade Next.js 14 web frontend for nationwide Kenya flood early warning system. Consumes FastAPI backend for real-time risk assessment, 3D simulation visualization, and alert management.

**Objective**: Enable decision-makers to interpret flood risk spatially and temporally, supporting 60-minute early warning lead time.

## Architecture

### Tech Stack
- **Framework**: Next.js 14 (App Router), React 18, TypeScript
- **Mapping**: Mapbox GL JS v3 (Kenya choropleth)
- **3D Visualization**: CesiumJS (flood propagation animation)
- **Data Fetching**: TanStack React Query v5 (caching + auto-refresh)
- **State**: Zustand (global app state)
- **Charts**: Recharts (time-series trends)
- **Forms**: React Hook Form + Zod (validation)
- **Auth**: NextAuth.js (JWT wrapping backend)
- **Styling**: Tailwind CSS 3 (accessibility-first)
- **Icons**: Lucide React
- **Real-time**: Native WebSocket (Redis pub/sub)

### Pages

#### `/` (Dashboard)
- Full-screen Mapbox choropleth of 47 Kenya counties
- Colour-coded by risk level (green/yellow/orange/red)
- Click county → side panel with SHAP explanations
- Time-series 6h risk trend chart
- "Trigger 3D Simulation" button
- Live alert ticker (WebSocket-driven marquee)
- Data freshness badge (IMERG update time, barometer count)

#### `/simulate/[county_code]` (3D Viewer)
- Cesium.js terrain viewer for selected county
- Animated flood propagation (play/pause/scrub)
- Node risk markers colour-coded by score
- "Weakness points" (high-risk junctions) pulsing
- Timeline slider for frame scrubbing
- GeoJSON export button

#### `/alerts` (SMS/USSD Dispatch)
- Multi-language message composer (EN/SW/Sheng)
- Risk level selector (visual badges)
- Preview of SMS/USSD messages (≤160/≤182 chars)
- Phone number input (E.164 format)
- Message type selector (SMS vs USSD)
- Delivery tracking table
- **Objective**: Support >90% SMS reach via Africa's Talking

#### `/admin` (Admin-only Dashboard)
- **EKF Tuning**: Update rainfall fusion sensitivity per county
  - Pressure sensitivity slider (barometer → rainfall conversion)
  - Process noise (Q) slider
  - Measurement noise (R) slider
  - All changes audit-logged
- **Model Retrain**: Queue GATv2 retraining with date range
  - Start/end date picker (default: 30d)
  - Synthetic data toggle
  - Job status tracking
- **Volunteer Devices**: Registry of barometer contributors
  - Device ID (hashed), county, reading count, last reading
  - Paginated table
- **Audit Logs**: Immutable operational changes
  - Event type, user, timestamp, old/new values
  - Pagination

### Components

#### Map Components
- **KenyaRiskMap.tsx**: Mapbox GL choropleth
  - GiST spatial index integration
  - Hover effects + county selection
  - Legend with accessibility labels
  - Fit-bounds animation on county select

- **CountySidePanel.tsx**: Risk details panel
  - Risk badge + gauge (0-100%)
  - Time-series chart (Recharts)
  - Risk node cards with expandable SHAP factors
  - Simulation trigger button

#### Simulation
- **CesiumViewer.tsx**: 3D wrapper
  - Timeline slider + frame counter
  - Weakness points indicator (pulsing)
  - Frame selection
  
- **CesiumCanvas.tsx**: Direct Cesium integration
  - Lazy-loaded to avoid bundle bloat
  - Terrain + flood extent + node markers
  - Colour-coded by risk score

#### Charts
- **RiskTrendChart.tsx**: 6h time-series
  - Recharts line chart
  - Current + previous risk comparison (↑/↓)
  - Interpretation hint

#### Forms
- **AlertComposer.tsx**: Alert dispatch
  - Multi-language preview
  - Phone number validation
  - SMS/USSD character counter
  - Delivery status tracking

#### Admin
- **EKFTuner.tsx**: Rainfall fusion calibration
  - Physics-based sliders (Overeem et al. 2019 model)
  - Real-time parameter updates
  - Audit log integration

- **ModelRetrain.tsx**: Model retraining job queue
  - Date range selector
  - Synthetic data toggle
  - Job tracking

#### Common UI
- **Skeleton.tsx**: Loading placeholders (WCAG AA)
- **ErrorBoundary.tsx**: Error recovery UI
- **RiskBadge.tsx**: Risk level badges + gauges

### Hooks

#### useRiskData()
```typescript
const { data, isLoading, error } = useRiskData(countyCode);
```
- React Query hook for risk heatmap fetching
- 30s auto-refresh (matches backend Celery schedule)
- 25s cache + keep-previous-data
- 2 retries with exponential backoff

#### useSimulation()
```typescript
const triggerSim = useTriggerSimulation();
await triggerSim.mutateAsync(countyCode);
```
- Mutation hook for POST /simulate
- 3h duration, 5min step interval
- Returns frames + weakness points

#### useWebSocket()
```typescript
useWebSocket({
  countyCode: 'KEN01',
  onMessage: (event) => { /* update state */ },
  autoReconnect: true,
});
```
- Auto-reconnect with exponential backoff
- County-specific or national subscriptions (query param)
- Handles disconnections gracefully

### Global State (Zustand)

```typescript
useAppStore()
├── selectedCountyCode: string | null
├── isAdmin: boolean
├── simulationId: string | null
├── alertQueue: Alert[]
├── dataFreshness
│   ├── lastIMERG: ISO string
│   └── lastBarometerCount: number
└── [setters + getAlerts(), updateLastIMERG(), etc.]
```

## Accessibility (WCAG 2.1 AA)

✅ Colour contrast ratios meet AA standards (4.5:1 text)
✅ Dark mode (Mapbox dark-v11) reduces blue light
✅ Keyboard navigable (arrow keys, Tab, Enter)
✅ Focus indicators (savanna-gold outline)
✅ Semantic HTML (<button>, <section>, <main>)
✅ ARIA labels on all interactive elements
✅ Loading skeletons with aria-busy
✅ Error boundaries with fallback UI
✅ Screen reader support (role="region", aria-label)

### Kenyan Colour Palette
- **Maasai Red**: #8B0000 (primary accent)
- **Savanna Gold**: #D4AF37 (buttons, highlights)
- **Kenya Green**: #39A900 (success states)
- **Risk colours**: 
  - Low: #10B981 (emerald)
  - Medium: #F59E0B (amber)
  - High: #EF4444 (red)
  - Critical: #7F1D1D (dark red)

## API Integration

### Endpoint Consumption

| Endpoint | Method | Hook/Component | Purpose |
|----------|--------|---|---------|
| `/risk/{county_code}` | GET | useRiskData | Fetch latest risk assessment |
| `/simulate` | POST | useTriggerSimulation | Queue 3D simulation |
| `/ingest/barometer` | POST | (Android → backend) | Submit device readings |
| `/alerts/send` | POST | AlertComposer | Dispatch SMS/USSD |
| `/auth/token` | POST | NextAuth (login) | Authenticate user |
| `/admin/ekf-tune` | POST | EKFTuner | Update EKF parameters |
| `/admin/retrain` | POST | ModelRetrain | Queue model job |
| `/admin/audit-logs` | GET | AdminPage | Fetch audit trail |
| `/ws/live` | WS | useWebSocket | Real-time risk updates |

### Error Handling
- Axios interceptor catches 401 (signed out)
- React Query retry logic (2 retries, exponential backoff)
- Error Boundary catches render errors
- User-friendly fallback UI

## Performance Optimizations

- **Dynamic imports**: CesiumJS (lazy-loaded)
- **Image optimization**: Next.js Image component
- **Code splitting**: Route-based (App Router)
- **Caching strategy**: 25s stale time, keep-previous-data
- **Bundle analysis**: next/bundle-analyzer available
- **Minification**: SWC compiler (next/swc)

## Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=pk_test_xxx
NEXTAUTH_SECRET=random32charstring
NEXTAUTH_URL=http://localhost:3000
NODE_ENV=development
```

## Development

```bash
# Install dependencies
npm install

# Development server (hot reload)
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
npm start
```

## Deployment

### Vercel (Recommended)
```bash
vercel deploy
```

### Docker
```bash
docker build -t floodguard-fe .
docker run -p 3000:3000 floodguard-fe
```

### Environment Setup
- Mapbox token required (free tier available)
- Backend URL must be accessible (CORS enabled)
- NextAuth secret generated: `openssl rand -base64 32`

## Testing

Run unit & integration tests:
```bash
npm test
npm run test:coverage
```

Cypress E2E tests:
```bash
npm run test:e2e
```

## Notable Decisions

1. **React Query over SWR**: Richer cache control, pagination support
2. **Zustand over Redux**: Lighter bundle, simpler API
3. **TailwindCSS**: Rapid iteration + accessibility defaults
4. **Native WebSocket**: FCM/Pusher would add latency; Redis pub/sub direct is faster
5. **Dynamic Cesium import**: Avoids 3MB bundle penalty on dashboard load
6. **NextAuth.js**: Abstracts JWT logic, auto-refresh tokens
7. **Dark theme default**: Reduces eye strain for 24/7 monitoring ops

## Debugging

Enable debug logging:
```typescript
localStorage.setItem('debug', 'floodguard:*');
```

Browser DevTools:
- React Query DevTools (installed but hidden in prod)
- Mapbox GL JS inspector (Ctrl+Shift+I in map)
- Cesium Inspector (Cesium.Ion browser)

## Support & Maintenance

- **Update Next.js**: `npm update next react react-dom`
- **Monitor bundle size**: `npm run build && npm run analyze`
- **Security patches**: Dependabot + automated PRs
- **Performance monitoring**: Web Vitals integrated

---
**Version**: 1.0.0 | **Last Updated**: 2026-04-20
