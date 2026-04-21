# PRODUCTION DEPLOYMENT ARCHITECTURE

Multi-cloud deployment architecture for FloodGuard KE with 99.9% uptime SLA, auto-scaling, disaster recovery, and cost optimization.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Edge)                         │
├──────────────────────┬──────────────────┬──────────────────────┤
│   Web Browser        │  Mobile Apps     │  Third-Party API     │
│   (Next.js → CDN)    │  (Android Play)  │  (County Offices)    │
└──────────────────────┴──────────────────┴──────────────────────┘
                           ↓ HTTPS (TLS 1.3)
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                             │
├──────────────────────────────────────────────────────────────────┤
│  • CloudFlare / AWS API Gateway (rate limiting, DDoS)            │
│  • JWT token validation + refresh                                │
│  • Request logging → CloudWatch                                  │
│  • Geographic routing (nearest region)                           │
└──────────────────────────────────────────────────────────────────┘
                           ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│              KUBERNETES / ECS CONTAINER LAYER                    │
├──────────────────────┬──────────────────┬──────────────────────┤
│  FastAPI Backend     │   Celery Workers │   Celery Beat        │
│  (3 replicas auto)   │   (5 replicas)   │   (1 replica)        │
│  8 CPU, 16GB RAM     │   8 CPU, 16GB    │   2 CPU, 4GB         │
│  (us-east-1a/b/c)    │   (us-east-1)    │   (us-east-1a)       │
└──────────────────────┴──────────────────┴──────────────────────┘
    ↓ (TCP 5432)           ↓ (Redis)          ↓ (PostgreSQL)
┌─────────────────────────────────────────────────────────────────┐
│                  DATA PERSISTENCE LAYER                          │
├──────────────────┬────────────────────┬──────────────────────────┤
│  RDS PostgreSQL  │  ElastiCache Redis │  S3 Data Lake           │
│  • Multi-AZ      │  • 6 nodes cluster │  • Simulation outputs   │
│  • Read replicas │  • Auto-failover   │  • Model checkpoints    │
│  • Automated     │  • Pub/Sub Streams │  • GeoTIFF rasters      │
│    backups       │                    │                          │
└──────────────────┴────────────────────┴──────────────────────────┘
    ↓ Event Stream (SNS/SQS)
┌─────────────────────────────────────────────────────────────────┐
│              ANALYTICS & MONITORING LAYER                        │
├──────────────────────────────────────────────────────────────────┤
│  • CloudWatch → Grafana dashboards                               │
│  • Datadog / New Relic (APM monitoring)                          │
│  • Splunk (audit logs, compliance)                               │
│  • PagerDuty (on-call alerting)                                  │
│  • BigQuery (data warehouse for BI)                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. AWS Deployment (Recommended)

### 2.1 Infrastructure-as-Code (Terraform)

**terraform/main.tf**:

```hcl
# AWS Provider
provider "aws" {
  region = var.aws_region  # us-east-1
}

# VPC (Virtual Private Cloud)
resource "aws_vpc" "floodguard" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
}

# Public Subnets (3 AZs for HA)
resource "aws_subnet" "public" {
  count             = 3
  vpc_id            = aws_vpc.floodguard.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# Private Subnets (RDS + ElastiCache)
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.floodguard.id
  cidr_block        = "10.0.${count.index + 100}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# RDS PostgreSQL (Multi-AZ)
resource "aws_db_instance" "postgres" {
  identifier              = "floodguard-postgres"
  instance_class         = "db.r6i.2xlarge"  # 8 vCPU, 64GB RAM
  engine                 = "postgres"
  engine_version         = "15.2"
  allocated_storage      = 500  # GB
  storage_type           = "gp3"
  multi_az              = true
  backup_retention_days = 30
  
  db_name               = "floodguard"
  username              = "postgres"
  password              = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.private.name
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled     = true
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn
}

# ElastiCache Redis Cluster
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "floodguard-redis"
  engine               = "redis"
  node_type            = "cache.r6g.xlarge"  # 32GB per node
  num_cache_nodes      = 6
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name      = aws_elasticache_subnet_group.private.name
  security_group_ids     = [aws_security_group.redis.id]
  automatic_failover_enabled = true
  
  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

# ECS Cluster (Elastic Container Service)
resource "aws_ecs_cluster" "floodguard" {
  name = "floodguard-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition (FastAPI)
resource "aws_ecs_task_definition" "backend" {
  family                   = "floodguard-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"   # 2 vCPU
  memory                   = "4096"   # 4 GB
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://${aws_db_instance.postgres.username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/floodguard"
      },
      {
        name  = "REDIS_URL"
        value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
      }
    ]
    secrets = [
      {
        name      = "JWT_SECRET_KEY"
        valueFrom = aws_secretsmanager_secret.jwt_key.arn
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# Service (Auto-scaling)
resource "aws_ecs_service" "backend" {
  name            = "floodguard-backend"
  cluster         = aws_ecs_cluster.floodguard.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 3
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
}

# Auto Scaling (Scales 1-10 tasks based on CPU/Memory)
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 10
  min_capacity       = 3
  resource_id        = "service/${aws_ecs_cluster.floodguard.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  policy_name            = "cpu-autoscaling"
  policy_type            = "TargetTrackingScaling"
  resource_id            = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension     = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace      = aws_appautoscaling_target.ecs_target.service_namespace
  target_tracking_scaling_policy_configuration {
    target_value = 75.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# ALB (Application Load Balancer)
resource "aws_lb" "backend" {
  name               = "floodguard-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]
}

# Target Group (Health checks every 30s)
resource "aws_lb_target_group" "backend" {
  name        = "floodguard-backend"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.floodguard.id
  
  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
}

# ACM SSL Certificate (Let's Encrypt-compatible)
resource "aws_acm_certificate" "floodguard" {
  domain_name       = "api.floodguard.ke"
  validation_method = "DNS"
}

# CloudFront CDN (Cache HTML/JS/CSS from Vercel)
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = "floodguard-ke.vercel.app"
    origin_id   = "vercel"
  }
  
  enabled = true
  
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "vercel"
    
    forwarded_values {
      query_string = true
    }
    
    viewer_protocol_policy = "redirect-to-https"
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["KE"]
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# S3 bucket for data lake
resource "aws_s3_bucket" "data_lake" {
  bucket = "floodguard-data-lake"
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# SNS Topic (Alert notifications)
resource "aws_sns_topic" "alerts" {
  name = "floodguard-alerts"
}

# SQS Queue (Async job processing)
resource "aws_sqs_queue" "report_generation" {
  name                       = "floodguard-reports"
  visibility_timeout_seconds = 3600
  message_retention_seconds  = 86400
}

# Secrets Manager (Store sensitive data)
resource "aws_secretsmanager_secret" "jwt_key" {
  name = "floodguard/jwt-secret-key"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/floodguard-backend"
  retention_in_days = 30
}
```

### 2.2 Deployment Steps

```bash
# 1. Install Terraform + AWS CLI
brew install terraform awscli

# 2. Configure AWS credentials
aws configure
# AWS Access Key ID: [your key]
# AWS Secret Access Key: [your secret]
# Default region: us-east-1

# 3. Format + validate Terraform
cd terraform
terraform fmt
terraform validate

# 4. Plan infrastructure
terraform plan -out=tfplan

# 5. Apply infrastructure
terraform apply tfplan

# 6. Build + push Docker image
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker build -t floodguard-backend:1.0.0 .
docker tag floodguard-backend:1.0.0 123456789.dkr.ecr.us-east-1.amazonaws.com/floodguard-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/floodguard-backend:latest

# 7. Deploy to ECS (auto-triggered by image push)
```

### 2.3 AWS Cost Estimation (Monthly)

| Service | Size | Cost |
|---------|------|------|
| **RDS PostgreSQL** | db.r6i.2xlarge (8 CPU, 64GB) | $1,800 |
| **ElastiCache Redis** | 6 nodes cache.r6g.xlarge | $1,200 |
| **ECS Fargate** | 3 tasks × 2vCPU × 4GB (30 days) | $800 |
| **Celery Workers** | 5 tasks × 1vCPU × 2GB | $400 |
| **ALB** | 1 ALB + data processing | $200 |
| **CloudFront CDN** | 1TB data transfer | $150 |
| **S3 Data Lake** | 1TB storage + access | $50 |
| **CloudWatch + Logs** | Monitoring + 30-day retention | $100 |
| **Secrets Manager** | 1 secret | $10 |
| **Data Transfer (Outbound)** | 50GB to Kenya networks | $250 |
| **TOTAL** | | **~$5,000/month** |

---

## 3. Google Cloud Deployment (Alternative)

### 3.1 Architecture Components

```yaml
# Cloud SQL (PostgreSQL)
- instance_class: db-custom-8-65536  # 8 CPU, 64GB RAM
- region: africa-south1  # South Africa (nearest to Kenya)
- backup_location: africa-south1
- ha_enabled: true
- automated_backups: daily

# Cloud Memorystore (Redis)
- tier: standard
- memory_size_gb: 200  # 6 nodes × 32GB
- region: africa-south1
- enable_auth: true
- automatic_failover: enabled

# Cloud Run (Container orchestration)
- service: floodguard-backend
- memory: 4Gi
- cpu: 2
- min_instances: 3
- max_instances: 50
- timeout: 3600s
- min_concurrency: 50

# Pub/Sub (Message streaming)
- topic: floodguard-alerts
- subscriptions:
  - push-to-frontend (WebSocket push)
  - archive-to-bigquery (data warehouse)

# Cloud Tasks (Job scheduling)
- queue: celery-tasks
- rate_limit: 10,000 tasks/sec

# Cloud Storage (Data lake)
- bucket: floodguard-data-lake
- storage_class: STANDARD
- versioning: enabled
- encryption: CMK

# BigQuery (Data warehouse)
- project: floodguard-ke
- region: africa-south1
```

### 3.2 Deployment (gcloud CLI)

```bash
# Export backend image to Artifact Registry
gcloud auth configure-docker africa-south1-docker.pkg.dev

docker build -t floodguard-backend:1.0.0 .
docker tag floodguard-backend:1.0.0 \
  africa-south1-docker.pkg.dev/floodguard-ke/docker/backend:latest

docker push africa-south1-docker.pkg.dev/floodguard-ke/docker/backend:latest

# Deploy to Cloud Run
gcloud run deploy floodguard-backend \
  --image africa-south1-docker.pkg.dev/floodguard-ke/docker/backend:latest \
  --platform managed \
  --region africa-south1 \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 3 \
  --max-instances 50 \
  --set-env-vars DATABASE_URL=$DB_URL,REDIS_URL=$REDIS_URL \
  --no-allow-unauthenticated

# Enable Cloud SQL Proxy
gcloud run services update floodguard-backend \
  --add-cloudsql-instances floodguard-postgres \
  --update-env-vars CLOUDSQL_CONNECTION_NAME=floodguard-postgres
```

---

## 4. Kubernetes Deployment (Enterprise)

### 4.1 Helm Chart (kubernetes/floodguard-helm)

```yaml
# values.yaml
replicaCount: 3

image:
  repository: registry.floodguard.ke/floodguard-backend
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 8000
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.floodguard.ke
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: floodguard-tls
      hosts:
        - api.floodguard.ke

resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: postgres-secret
        key: connection-string
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: redis-secret
        key: connection-string

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 4.2 Deployment

```bash
# Add Helm repo
helm repo add floodguard https://helm.floodguard.ke

# Install chart
helm install floodguard floodguard/floodguard \
  -n floodguard --create-namespace \
  -f kubernetes/values.yaml

# Monitor deployment
kubectl rollout status deployment/floodguard-backend -n floodguard

# Scale manually
kubectl scale deployment floodguard-backend --replicas=10 -n floodguard
```

---

## 5. Database Replication & Backup

### 5.1 PostgreSQL Replication

```sql
-- Primary server (production)
CREATE PUBLICATION floodguard FOR ALL TABLES;

-- Standby server (read-only replica)
CREATE SUBSCRIPTION floodguard_subscriber
CONNECTION 'postgresql://user:pass@primary.floodguard.ke/floodguard'
PUBLICATION floodguard;

-- Backup schedule
-- Daily at 02:00 UTC
pg_dump -h primary.floodguard.ke -U postgres floodguard | \
  gzip > /backup/floodguard-$(date +%Y%m%d).sql.gz

# Retention: 30 latest backups
find /backup -name "floodguard-*.sql.gz" -mtime +30 -delete

-- Full restore (disaster recovery)
psql -h standby.floodguard.ke < /backup/floodguard-20240420.sql
```

### 5.2 Redis Persistence

```
# redis.conf
save 900 1      # Save if 1 key changed in 900 seconds
save 300 10     # Save if 10 keys changed in 300 seconds
save 60 10000   # Save if 10000 keys changed in 60 seconds

appendonly yes
appendfsync everysec

# AOF (Append-Only File) provides durability
# RDB snapshots provide fast recovery
```

---

## 6. Monitoring & Alerting

### 6.1 Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'floodguard-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

### 6.2 Alert Rules

```yaml
# alerts.yaml
groups:
  - name: floodguard
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        annotations:
          summary: "High error rate detected"
          
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        annotations:
          summary: "PostgreSQL database is down"
          
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        annotations:
          summary: "Redis cluster is down"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "P95 latency is {{$value}}s"
```

### 6.3 Grafana Dashboards

**Key metrics to visualize**:
- API response times (p50, p95, p99)
- Request throughput (req/sec)
- Error rate (5xx, 4xx)
- Database connection pool utilization
- Redis memory usage
- Celery task queue length
- Cost per request

---

## 7. Disaster Recovery Plan

| Scenario | RTO | RPO | Recovery |
|----------|-----|-----|----------|
| **Single server crash** | 5 min | 0 min | Auto-failover to standby |
| **Region outage** | 30 min | 1 hour | Restore from backup in different region |
| **Data corruption** | 2 hours | 1 day | Restore from 24h-old backup |
| **Cyber attack** | 4 hours | 1 day | Isolate, patch, restore from clean backup |

**RTO** = Recovery Time Objective (time to restore)
**RPO** = Recovery Point Objective (acceptable data loss)

---

## 8. Security Hardening

```bash
# 1. Network isolation (VPC security groups)
aws ec2 authorize-security-group-ingress --group-id sg-xxx \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0

# 2. Database encryption (at-rest + in-transit)
# RDS: Enable "Encryption at rest" in AWS console
# Redis: Enable "Transit Encryption" + "Authentication"

# 3. Secrets management
aws secretsmanager create-secret --name floodguard/jwt-key \
  --secret-string $(openssl rand -base64 32)

# 4. DDoS protection
# AWS Shield Standard (free, automatic)
# AWS WAF (Web Application Firewall) + rate limiting

# 5. SSL/TLS certificates
# ACM (AWS Certificate Manager) auto-renews every 90 days
# OR Let's Encrypt + cert-bot for auto-renewal

# 6. Audit logging
# CloudTrail: Log all API calls
# RDS Enhanced Monitoring: Log query performance
# VPC Flow Logs: Log network traffic

# 7. IP whitelisting (Kubernetes)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
spec:
  podSelector:
    matchLabels:
      app: floodguard-backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
```

---

## 9. Cost Optimization

| Strategy | Savings |
|----------|---------|
| **Reserved Instances (1-year)** | 20-30% |
| **Spot Instances (Celery workers)** | 70-90% |
| **Auto-scaling (scale down at night)** | 15-25% |
| **Caching (Redis)** | Reduce database load 60% |
| **CDN (CloudFront)** | 50-70% bandwidth savings |
| **Data compression** | 40% storage savings |
| **Multi-region failover** | Share resources across regions |

---

## 10. Deployment Timeline

| Phase | Timeline | Task |
|-------|----------|------|
| **Week 1** | Day 1-2 | Provision AWS infrastructure (VPC, RDS, ElastiCache, ECS) |
| | Day 3-4 | Deploy backend to ECS, test API endpoints |
| | Day 5-7 | Setup monitoring (CloudWatch, Prometheus, Grafana) |
| **Week 2** | Day 8-9 | Setup CI/CD pipeline (GitHub Actions → AWS) |
| | Day 10-11 | Deploy frontend to Vercel, configure CDN |
| | Day 12-14 | Load testing + performance tuning |
| **Week 3** | Day 15-16 | Security audit + hardening |
| | Day 17-18 | Disaster recovery drills |
| | Day 19-21 | UAT + stakeholder testing (Kenya County Offices) |
| **Week 4** | Day 22+ | Production launch + 24/7 monitoring |

---

## 11. Ongoing Operations

### Daily
- Monitor error rates + latency
- Check backup completion status
- Review security alerts

### Weekly
- Performance review (DB queries, cache hits)
- Dependency updates (security patches)
- Capacity planning (traffic trends)

### Monthly
- Cost analysis + optimization
- Disaster recovery drill
- Penetration testing
- Security audit

### Quarterly
- Database optimization (VACUUM, REINDEX)
- Capacity expansion planning
- Architecture review

---

**Production is GO!** 🚀

---
**Last Updated**: 2026-04-20 | **Version**: 1.0.0-prod
