# FloodGuard KE Backend - API Quick Reference

## Base URL
```
http://localhost:8000 (development)
https://api.floodguard.ke (production)
```

## Authentication

All endpoints (except /auth/token) require JWT bearer token.

```
Authorization: Bearer {access_token}
```

### Login
```http
POST /auth/token
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Barometer Ingestion

### Single Reading (Rate Limit: 60 req/min)
```http
POST /ingest/barometer
Authorization: Bearer {token}
Content-Type: application/json

{
  "device_id": "phone_abc123",
  "latitude": -1.29,
  "longitude": 36.82,
  "pressure_hpa": 1013.5,
  "altitude_m": 1600,
  "temperature_c": 25.3,
  "humidity_pct": 65.0,
  "timestamp": "2026-04-20T10:30:00Z"
}

Response:
{
  "id": 42,
  "timestamp": "2026-04-20T10:30:00+00:00",
  "created_at": "2026-04-20T10:30:15+00:00"
}
```

### Batch Ingestion (≤12 readings, Rate Limit: 30 req/min)
```http
POST /ingest/barometer/batch
Authorization: Bearer {token}
Content-Type: application/json

{
  "readings": [
    {
      "device_id": "phone_abc123",
      "latitude": -1.29,
      "longitude": 36.82,
      "pressure_hpa": 1013.5,
      "altitude_m": 1600,
      "temperature_c": 25.3,
      "humidity_pct": 65.0,
      "timestamp": "2026-04-20T10:30:00Z"
    },
    ...
  ]
}
```

---

## Risk Queries

### Get Heatmap (All Nodes)
```http
GET /risk/04
Authorization: Bearer {token}

Response (Nairobi county):
{
  "county_code": "04",
  "county_name": "Nairobi",
  "timestamp": "2026-04-20T10:30:00+00:00",
  "nodes": [
    {
      "node_id": "04_n0",
      "latitude": -1.295,
      "longitude": 36.815,
      "risk_score": 0.73,
      "depth_cm": 45.2,
      "shap_top3": [
        {
          "feature_name": "fused_rainfall_mm_h",
          "contribution": 0.52,
          "value": 12.5
        },
        {
          "feature_name": "imperv_fraction",
          "contribution": 0.31,
          "value": 0.85
        },
        {
          "feature_name": "drain_capacity_m3_s",
          "contribution": 0.17,
          "value": 3.2
        }
      ],
      "alert_en": "FloodGuard: HIGH flood risk in 04! Risk 73%. Move to high ground NOW.",
      "alert_sw": "FloodGuard: Hatari KUBWA 04! Jinga 73%. Panda mlimani SASA."
    },
    ...
  ],
  "max_risk_score": 0.85,
  "max_depth_cm": 62.1,
  "alert_level": "High"
}
```

---

## 3D Simulation

### Generate Frames (for Cesium.js)
```http
POST /simulate?county_code=04&duration_hours=3&step_minutes=15
Authorization: Bearer {token}

Response:
{
  "county_code": "04",
  "start_timestamp": "2026-04-20T10:30:00+00:00",
  "end_timestamp": "2026-04-20T13:30:00+00:00",
  "frames": [
    {
      "frame_index": 0,
      "timestamp": "2026-04-20T10:30:00+00:00",
      "nodes": [ ... ]  # Same structure as /risk
    },
    {
      "frame_index": 1,
      "timestamp": "2026-04-20T10:45:00+00:00",
      "nodes": [ ... ]  # Depth scaled by time
    },
    ...
  ],
  "duration_minutes": 180,
  "weakness_points": [
    {
      "node_id": "04_n5",
      "latitude": -1.285,
      "longitude": 36.825,
      "depth_cm": 98.5
    },
    ...
  ]
}
```

Query Params:
- `county_code` (required): "01" to "47"
- `duration_hours`: 1-6 (default 3)
- `step_minutes`: 5-60 (default 15)

---

## Alerts

### Send Alert
```http
POST /alerts/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "county_code": "04",
  "phone_number": "+254712345678",
  "language": "en",
  "include_shap": true
}

Response:
{
  "alert_id": 127,
  "county_code": "04",
  "channel": "sms",
  "sent_at": "2026-04-20T10:30:00+00:00",
  "delivery_status": "pending"
}
```

### Africa's Talking Webhook
```http
POST /alerts/at-delivery
Content-Type: application/json

{
  "id": "ATXid_0906f13c3ac6d92467c9b0b9e6b7a",
  "phoneNumber": "+254712345678",
  "status": "Success",
  "networkCode": "63902",
  "retryCount": 0
}
```

---

## WebSocket (Real-time)

### Subscribe to County
```
WS ws://localhost:8000/ws/live?county_code=04

Messages:
{
  "county_code": "04",
  "timestamp": "2026-04-20T10:30:00+00:00",
  "max_risk_score": 0.73,
  "max_depth_cm": 45.2
}
```

### Subscribe to National
```
WS ws://localhost:8000/ws/live

Messages:
{
  "alert_type": "critical",
  "affected_counties": ["04", "17"],
  "timestamp": "2026-04-20T10:30:00+00:00"
}
```

---

## Admin Endpoints

### Retrain Model
```http
POST /admin/retrain
Authorization: Bearer {admin_token}

Response:
{
  "job_id": "train_abc123",
  "status": "pending",
  "started_at": "2026-04-20T10:30:00+00:00"
}
```

### Tune EKF Parameters
```http
POST /admin/ekf-tune
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "county_code": "04",
  "process_noise": 0.02,
  "measurement_noise": 0.15,
  "reason": "Improving rainfall fusion accuracy"
}

Response:
{
  "status": "updated",
  "county_code": "04"
}
```

### Register Volunteer Device
```http
POST /admin/volunteers
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "device_id": "phone_abc123",
  "phone_number": "+254712345678",
  "county_code": "04",
  "language": "en"
}

Response:
{
  "device_id_hash": "5feceb66ffc86f38...",
  "phone_number_hash": "6d0a92e5b08ce1f1...",
  "county_code": "04",
  "registered_at": "2026-04-20T10:30:00+00:00"
}
```

### Get Audit Logs
```http
GET /admin/audit-logs?page=1&page_size=50
Authorization: Bearer {admin_token}

Response:
{
  "total": 127,
  "page": 1,
  "page_size": 50,
  "entries": [
    {
      "id": 1,
      "user_id": 1,
      "action": "ekf_tune",
      "resource_type": "ekf_params",
      "resource_id": "04",
      "changes": {
        "process_noise": 0.02,
        "measurement_noise": 0.15
      },
      "status": "success",
      "error_message": null,
      "created_at": "2026-04-20T10:30:00+00:00"
    },
    ...
  ]
}
```

---

## Health Check

```http
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2026-04-20T10:30:00+00:00",
  "components": {
    "database": "ok",
    "redis": "ok",
    "ml_model": "ok (v1.0.0)",
    "county_data": "ok"
  }
}
```

---

## Error Responses

All errors follow standard HTTP status codes:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common codes:
- `400` - Bad request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not found (county/county doesn't exist)
- `429` - Too many requests (rate limited)
- `500` - Internal server error

---

## Rate Limiting

- `/ingest/barometer`: 60 requests/minute per IP
- `/ingest/barometer/batch`: 30 requests/minute per IP
- `/simulate`: 10 requests/minute per IP
- Other endpoints: Unlimited (but subject to DB/Redis limits)

---

## OpenAPI / Swagger

Interactive API documentation:
```
GET /docs          # Swagger UI
GET /openapi.json  # OpenAPI spec
```

---

**Last Updated**: April 2026
