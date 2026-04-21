/**
 * FloodGuard KE TypeScript Type Definitions
 * Aligned with backend Pydantic schemas for type safety across API calls
 */

// Risk level classification (used throughout system for colour coding)
export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

// Geographic boundary for Kenya (latitude, longitude bounds)
export interface GeoLocation {
  latitude: number;
  longitude: number;
}

// Single risk assessment node (from GATv2 inference output)
export interface RiskNode {
  node_id: string;
  lat: number;
  lng: number;
  risk_score: number; // 0-1 float
  depth_cm: number;
  shap_top3: Array<{
    factor: string;
    contribution: number;
  }>;
  alert_message_en: string;
  alert_message_sw: string;
}

// County-level risk assessment response
export interface RiskHeatmapResponse {
  county_code: string;
  county_name: string;
  valid_time: string; // ISO 8601 timestamp
  county_risk_score: number; // 0-1 float
  risk_level: RiskLevel;
  nodes: RiskNode[];
}

// Single frame in flood simulation (time-stepped)
export interface SimulationFrame {
  t_minutes: number;
  nodes: Array<{
    node_id: string;
    lat: number;
    lng: number;
    risk_score: number;
    depth_cm: number;
  }>;
  flood_extent_geojson: GeoJSON.FeatureCollection;
}

// Weakness points: high-risk junctions identified by inference
export interface WeaknessPoint {
  node_id: string;
  lat: number;
  lng: number;
  risk_score: number;
  depth_cm: number;
}

// Complete simulation response (3D Cesium viewer input)
export interface SimulationResponse {
  simulation_id: string;
  county_code: string;
  duration_minutes: number;
  frames: SimulationFrame[];
  weakness_points: WeaknessPoint[];
}

// County metadata (for choropleth map)
export interface County {
  county_code: string;
  county_name: string;
  geometry: GeoJSON.MultiPolygon;
  centroid: {
    lat: number;
    lng: number;
  };
  population: number;
  is_urban: boolean;
}

// Barometer reading payload (180 bytes approx, from Android)
export interface BarometerPayload {
  device_id_hash: string; // SHA-256 hashed device ID
  pressure_hpa: number;
  altitude_m: number;
  accuracy: number;
  lat: number;
  lng: number;
  timestamp_device: string; // ISO 8601
}

// Alert SMS/USSD dispatch request
export interface AlertDispatchRequest {
  county_code: string;
  risk_level: RiskLevel;
  phone_numbers: string[]; // E.164 format
  message_type: 'sms' | 'ussd';
  language: 'en' | 'sw' | 'sheng';
}

// Alert dispatch response with delivery tracking
export interface AlertResponse {
  alert_id: string;
  county_code: string;
  message_type: 'sms' | 'ussd';
  recipient_count: number;
  created_at: string;
  status: 'pending' | 'sent' | 'delivered' | 'failed';
}

// Live WebSocket event from /ws/live
export interface WebSocketEvent {
  event: 'alert' | 'update' | 'warning';
  county_code?: string;
  county_risk_score?: number;
  risk_level?: RiskLevel;
  valid_time?: string;
  top_nodes?: RiskNode[];
  message?: string;
}

// JWT token response from /auth/token
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// User login request
export interface LoginRequest {
  email: string;
  password: string;
}

// Audit log entry (admin view)
export interface AuditLogEntry {
  id: string;
  event_type: string;
  user_id: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  metadata: Record<string, any>;
  created_at: string;
}

// EKF tuning parameters (admin control)
export interface EKFTuneRequest {
  county_code: string;
  pressure_sensitivity: number; // mm/h per hPa/min
  process_noise_q: number;
  measurement_noise_r: number;
}

// Model retrain trigger (admin control)
export interface ModelRetrainRequest {
  start_date: string; // ISO date
  end_date: string; // ISO date
  include_synthetic_data: boolean;
}

// Volunteer device registry (barometer contributors)
export interface VolunteerDevice {
  device_id_hash: string;
  county_code: string;
  created_at: string;
  last_reading_at?: string;
  reading_count: number;
}

// Admin-only paginated audit log response
export interface PaginatedAuditLogs {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Frontend state types (Zustand store)
export interface AppState {
  selectedCountyCode: string | null;
  isAdmin: boolean;
  simulationId: string | null;
  alertQueue: Array<{ id: string; type: RiskLevel; message: string }>;
  dataFreshness: {
    lastIMERG: string | null;
    lastBarometerCount: number;
  };
}

// Session state (NextAuth)
export interface Session {
  user: {
    email: string;
    id: string;
  };
  accessToken: string;
  refreshToken: string;
  isAdmin: boolean;
}

// GeoJSON types (for TypeScript safety)
namespace GeoJSON {
  export interface Position extends Array<number> {
    0: number;
    1: number;
    2?: number;
  }

  export interface Point {
    type: 'Point';
    coordinates: Position;
  }

  export interface MultiPolygon {
    type: 'MultiPolygon';
    coordinates: Position[][][][];
  }

  export interface Feature {
    type: 'Feature';
    geometry: Point | MultiPolygon | any;
    properties: Record<string, any>;
  }

  export interface FeatureCollection {
    type: 'FeatureCollection';
    features: Feature[];
  }
}

export type GeoJSON = GeoJSON.FeatureCollection;

// API Response wrapper for consistent error handling
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    code: string;
  };
}
