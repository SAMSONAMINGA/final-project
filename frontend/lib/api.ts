import axios, { type AxiosInstance } from 'axios';
import type {
  AlertDispatchRequest,
  AlertResponse,
  AuditLogEntry,
  EKFTuneRequest,
  LoginRequest,
  ModelRetrainRequest,
  PaginatedAuditLogs,
  RiskHeatmapResponse,
  RiskLevel,
  RiskNode,
  SimulationFrame,
  SimulationResponse,
  TokenResponse,
  VolunteerDevice,
  WebSocketEvent,
  WeaknessPoint,
} from '@/types/floodguard';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type BackendShapFactor = {
  feature_name?: string;
  factor?: string;
  contribution?: number;
  value?: unknown;
};

type BackendNodeRisk = {
  node_id: string;
  latitude?: number;
  longitude?: number;
  lat?: number;
  lng?: number;
  risk_score: number;
  depth_cm: number;
  shap_top3?: BackendShapFactor[];
  alert_en?: string;
  alert_sw?: string;
  alert_message_en?: string;
  alert_message_sw?: string;
};

type BackendRiskHeatmapResponse = {
  county_code: string;
  county_name: string;
  timestamp?: string;
  valid_time?: string;
  nodes: BackendNodeRisk[];
  max_risk_score?: number;
  county_risk_score?: number;
  alert_level?: RiskLevel;
  risk_level?: RiskLevel;
};

type BackendSimulationFrame = {
  frame_index?: number;
  t_minutes?: number;
  timestamp?: string;
  nodes: BackendNodeRisk[];
  flood_extent_geojson?: SimulationFrame['flood_extent_geojson'];
};

type BackendSimulationResponse = {
  simulation_id?: string;
  county_code: string;
  duration_minutes: number;
  frames: BackendSimulationFrame[];
  weakness_points: Array<BackendNodeRisk | WeaknessPoint>;
};

type BackendAuditLogEntry = {
  id: number | string;
  user_id?: number | string | null;
  action?: string;
  event_type?: string;
  changes?: Record<string, unknown> | null;
  new_values?: Record<string, unknown>;
  created_at: string;
};

type BackendAuditLogsResponse = {
  total: number;
  page: number;
  page_size: number;
  entries?: BackendAuditLogEntry[];
  items?: BackendAuditLogEntry[];
};

type BackendVolunteerDevicesResponse = {
  devices?: VolunteerDevice[];
  total_devices?: number;
};

class FloodGuardApi {
  private readonly client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async login(request: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/token', {
      username: request.email,
      password: request.password,
    });

    return response.data;
  }

  async getRiskHeatmap(countyCode: string): Promise<RiskHeatmapResponse> {
    const response = await this.client.get<BackendRiskHeatmapResponse>(
      `/risk/${encodeURIComponent(countyCode)}`,
    );

    return adaptRiskHeatmap(response.data);
  }

  async triggerSimulation(
    countyCode: string,
    durationHours = 3,
    stepMinutes = 5,
  ): Promise<SimulationResponse> {
    const response = await this.client.post<BackendSimulationResponse>(
      '/simulate',
      null,
      {
        params: {
          county_code: countyCode,
          duration_hours: durationHours,
          step_minutes: stepMinutes,
        },
      },
    );

    return adaptSimulation(response.data);
  }

  async sendAlert(request: AlertDispatchRequest): Promise<AlertResponse[]> {
    const responses = await Promise.all(
      request.phone_numbers.map((phoneNumber) =>
        this.client.post<{
          alert_id: number;
          county_code: string;
          channel: 'sms' | 'ussd';
          sent_at: string;
          delivery_status: AlertResponse['status'];
        }>('/alerts/send', {
          county_code: request.county_code,
          phone_number: phoneNumber,
          language: request.language === 'sheng' ? 'sh' : request.language,
          include_shap: true,
        }),
      ),
    );

    return responses.map(({ data }) => ({
      alert_id: String(data.alert_id),
      county_code: data.county_code,
      message_type: data.channel,
      recipient_count: 1,
      created_at: data.sent_at,
      status: data.delivery_status,
    }));
  }

  async tuneEKFParameters(request: EKFTuneRequest): Promise<{ status: string }> {
    const response = await this.client.post<{ status: string }>('/admin/ekf-tune', {
      county_code: request.county_code,
      process_noise: request.process_noise_q,
      measurement_noise: request.measurement_noise_r,
      reason: `Pressure sensitivity: ${request.pressure_sensitivity}`,
    });

    return response.data;
  }

  async triggerModelRetrain(
    _request: ModelRetrainRequest,
  ): Promise<{ job_id: string; status: string; started_at: string }> {
    const response = await this.client.post<{
      job_id: string;
      status: string;
      started_at: string;
    }>('/admin/retrain');

    return response.data;
  }

  async getVolunteerDevices(): Promise<VolunteerDevice[]> {
    const response =
      await this.client.get<BackendVolunteerDevicesResponse>('/admin/volunteers');

    return response.data.devices ?? [];
  }

  async getAuditLogs(page = 1, pageSize = 20): Promise<PaginatedAuditLogs> {
    const response = await this.client.get<BackendAuditLogsResponse>(
      '/admin/audit-logs',
      {
        params: {
          page,
          page_size: pageSize,
        },
      },
    );

    const items = response.data.items ?? response.data.entries ?? [];

    return {
      items: items.map(adaptAuditLog),
      total: response.data.total,
      page: response.data.page,
      page_size: response.data.page_size,
      total_pages: Math.ceil(response.data.total / response.data.page_size),
    };
  }

  connectWebSocket(
    onMessage: (event: WebSocketEvent) => void,
    onError?: (error: Event) => void,
    countyCode?: string,
  ): WebSocket {
    const wsBaseURL = API_URL.replace(/^http/, 'ws');
    const url = new URL('/ws/live', wsBaseURL);

    if (countyCode) {
      url.searchParams.set('county_code', countyCode);
    }

    const socket = new WebSocket(url.toString());

    socket.onmessage = (message) => {
      try {
        onMessage(JSON.parse(message.data) as WebSocketEvent);
      } catch {
        onMessage({ event: 'update', message: message.data });
      }
    };

    if (onError) {
      socket.onerror = onError;
    }

    return socket;
  }
}

function adaptRiskHeatmap(
  response: BackendRiskHeatmapResponse,
): RiskHeatmapResponse {
  const riskScore = response.county_risk_score ?? response.max_risk_score ?? 0;

  return {
    county_code: response.county_code,
    county_name: response.county_name,
    valid_time:
      response.valid_time ?? response.timestamp ?? new Date().toISOString(),
    county_risk_score: riskScore,
    risk_level: response.risk_level ?? response.alert_level ?? riskLevelFromScore(riskScore),
    nodes: response.nodes.map(adaptRiskNode),
  };
}

function adaptSimulation(response: BackendSimulationResponse): SimulationResponse {
  return {
    simulation_id: response.simulation_id ?? `${response.county_code}-${Date.now()}`,
    county_code: response.county_code,
    duration_minutes: response.duration_minutes,
    frames: response.frames.map((frame, index) => ({
      t_minutes: frame.t_minutes ?? index * 5,
      nodes: frame.nodes.map((node) => ({
        node_id: node.node_id,
        lat: node.lat ?? node.latitude ?? 0,
        lng: node.lng ?? node.longitude ?? 0,
        risk_score: node.risk_score,
        depth_cm: node.depth_cm,
      })),
      flood_extent_geojson:
        frame.flood_extent_geojson ??
        ({
          type: 'FeatureCollection',
          features: [],
        } as SimulationFrame['flood_extent_geojson']),
    })),
    weakness_points: response.weakness_points.map((point) => ({
      node_id: point.node_id,
      lat: point.lat ?? ('latitude' in point ? point.latitude ?? 0 : 0),
      lng: point.lng ?? ('longitude' in point ? point.longitude ?? 0 : 0),
      risk_score: point.risk_score,
      depth_cm: point.depth_cm,
    })),
  };
}

function adaptRiskNode(node: BackendNodeRisk): RiskNode {
  return {
    node_id: node.node_id,
    lat: node.lat ?? node.latitude ?? 0,
    lng: node.lng ?? node.longitude ?? 0,
    risk_score: node.risk_score,
    depth_cm: node.depth_cm,
    shap_top3:
      node.shap_top3?.map((factor) => ({
        factor: factor.factor ?? factor.feature_name ?? 'unknown',
        contribution: factor.contribution ?? 0,
      })) ?? [],
    alert_message_en: node.alert_message_en ?? node.alert_en ?? '',
    alert_message_sw: node.alert_message_sw ?? node.alert_sw ?? '',
  };
}

function adaptAuditLog(entry: BackendAuditLogEntry): AuditLogEntry {
  return {
    id: String(entry.id),
    event_type: entry.event_type ?? entry.action ?? 'unknown',
    user_id: String(entry.user_id ?? 'system'),
    new_values: entry.new_values ?? entry.changes ?? undefined,
    metadata: {},
    created_at: entry.created_at,
  };
}

function riskLevelFromScore(score: number): RiskLevel {
  if (score < 0.33) return 'Low';
  if (score < 0.66) return 'Medium';
  if (score < 0.85) return 'High';
  return 'Critical';
}

export const api = new FloodGuardApi(API_URL);
