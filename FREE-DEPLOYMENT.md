# FloodGuard KE - Free Deployment Guide

Deploy your entire stack **completely free** using:
- **Frontend**: Vercel (Next.js) - free tier
- **Backend**: Render (FastAPI) - free tier with auto-sleep
- **Database**: Neon (PostgreSQL) - free tier 3GB
- **Cache**: Upstash (Redis) - free tier
- **Task Queue**: Render Background Jobs - free
- **Storage**: AWS S3 free tier (12 months) + Cloudinary (free CDN)

---

## Prerequisites

- GitHub account (free)
- Vercel account (free, connect to GitHub)
- Render account (free)
- Neon account (free)
- Upstash account (free)
- Cloudinary account (free, optional for images)

---

## Step 1: Prepare Backend for Render

### 1.1 Update requirements.txt for compatibility

Render requires specific dependencies. Read your current requirements:

```bash
cd backend
# Add these if missing:
gunicorn==21.2.0          # Production WSGI server (required by Render)
python-multipart==0.0.6   # For form uploads
```

### 1.2 Create Render-specific files

**backend/render.yaml**:
```yaml
services:
  - type: web
    name: floodguard-backend
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHONUNBUFFERED
        value: true
      - key: DATABASE_URL
        scope: build
      - key: REDIS_URL
        scope: build
    
  - type: pserv
    name: floodguard-redis
    env: docker
    plan: free
    repo: https://github.com/redis/redis
```

### 1.3 Create runtime.txt

**backend/runtime.txt**:
```
python-3.11.7
```

### 1.4 Create .env.example

**backend/.env.example**:
```
# Database
DATABASE_URL=postgresql://user:password@host/floodguard
SQLALCHEMY_DATABASE_URL=postgresql://user:password@host/floodguard

# Cache
REDIS_URL=redis://default:password@host:6379

# Security
JWT_SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# API Keys (optional)
SENTRY_DSN=https://key@sentry.io/project
MAPBOX_API_KEY=your-mapbox-key

# Environment
ENVIRONMENT=production
DEBUG=False
```

---

## Step 2: Setup Free PostgreSQL (Neon)

### 2.1 Create Neon account & database

1. Go to https://neon.tech (click "Sign Up")
2. Sign in with GitHub (easiest)
3. Create new project:
   - Name: `floodguard-ke`
   - Region: `us-east-1` (cheapest, but slower from Kenya)
   - Database name: `floodguard`
4. Copy connection string: `postgresql://user:password@host/floodguard`

### 2.2 Run database migrations

On your laptop (not in production yet):

```bash
cd backend

# Set the database URL
export DATABASE_URL="postgresql://user:password@host/floodguard"

# Install dependencies
pip install -r requirements.txt

# Run migrations (Alembic)
alembic upgrade head

# Or manually create tables:
python -c "
from core.database import Base, engine
Base.metadata.create_all(bind=engine)
"
```

**Free tier limits**:
- 3GB storage ✓
- 5 connections ✓
- 1 CPU shared ✓
- Auto-suspend after 1 week of inactivity (restart on next request)

---

## Step 3: Setup Free Redis (Upstash)

### 3.1 Create Upstash account & database

1. Go to https://upstash.com (click "Sign Up")
2. Choose "Redis"
3. Create database:
   - Name: `floodguard-cache`
   - Region: `us-east-1`
4. Copy "UPSTASH_REDIS_REST_URL" and "UPSTASH_REDIS_REST_TOKEN"
5. Build connection string: `redis://default:token@host:port`

### 3.2 Update backend for Upstash

Upstash requires different client. Update **backend/main.py**:

```python
import os
from redis import Redis
from upstash_redis import Redis as UpstashRedis

# Use Upstash SDK
if "upstash" in os.getenv("REDIS_URL", ""):
    redis_client = UpstashRedis.from_env()
else:
    redis_client = Redis.from_url(os.getenv("REDIS_URL"))
```

**Free tier limits**:
- 10,000 commands/day ✓
- 1GB storage ✓
- REST API only (vs. TCP)

---

## Step 4: Push to GitHub

### 4.1 Initialize git (if not already)

```bash
cd /path/to/final\ project
git init
git config user.name "Your Name"
git config user.email "your@email.com"

git add .
git commit -m "Initial commit: FloodGuard KE full stack"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/floodguard-ke.git
git branch -M main
git push -u origin main
```

---

## Step 5: Deploy Backend to Render

### 5.1 Connect Render to GitHub

1. Go to https://render.com (sign up with GitHub)
2. Click "New +" → "Web Service"
3. Connect GitHub repo: `floodguard-ke`
4. Configure:
   - **Name**: `floodguard-backend`
   - **Environment**: `Docker` OR `Python`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Plan**: `Free`

### 5.2 Add environment variables

In Render dashboard, click service → "Environment":

```
DATABASE_URL=postgresql://...@neon.tech/floodguard
REDIS_URL=redis://default:token@upstash.com:...
JWT_SECRET_KEY=your-secret-key
ENVIRONMENT=production
DEBUG=False
```

### 5.3 Deploy

Click "Deploy" → wait 5-10 minutes → backend runs at `https://floodguard-backend.onrender.com`

**Free tier limits**:
- Auto-sleeps after 15 min inactivity (10-30s cold start)
- Shared CPU
- 512MB RAM ✓
- 1GB disk ✓

---

## Step 6: Deploy Frontend to Vercel

### 6.1 Configure Next.js for Vercel

**frontend/.env.local**:
```
NEXT_PUBLIC_API_URL=https://floodguard-backend.onrender.com
NEXT_PUBLIC_MAPBOX_TOKEN=pk_test_xxx  # Optional, Mapbox dark-v11 works free
```

### 6.2 Connect Vercel to GitHub

1. Go to https://vercel.com (sign up with GitHub)
2. Click "Import Project"
3. Select `floodguard-ke` repo
4. Configure:
   - **Framework**: Next.js
   - **Root Directory**: `frontend`
   - **Environment variables**: Add above
5. Deploy

**Frontend runs at**: `https://floodguard-ke.vercel.app`

**Free tier limits**:
- Unlimited deployments ✓
- Unlimited bandwidth (within reason) ✓
- Serverless functions (API routes) ✓
- Auto-scaling ✓

---

## Step 7: Setup Android App (Optional)

### 7.1 Build APK for distribution

```bash
cd android
./gradlew assembleRelease

# APK at: app/build/outputs/apk/release/app-release.apk
```

### 7.2 Host APK on GitHub Releases (free CDN)

```bash
cd /path/to/final\ project
git tag v1.0.0
git push origin v1.0.0

# Go to GitHub → Releases → Upload APK
```

Users can download from: `https://github.com/YOUR_USERNAME/floodguard-ke/releases`

---

## Step 8: Setup CI/CD (GitHub Actions - Free)

### 8.1 Create workflow file

**`.github/workflows/deploy.yml`**:
```yaml
name: Deploy to Render & Vercel

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST https://api.render.com/deploy/srv-xxx?key=$RENDER_API_KEY

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
        run: |
          npm install -g vercel
          vercel deploy --prod --token $VERCEL_TOKEN --cwd frontend
```

### 8.2 Add secrets to GitHub

1. Go to repo → Settings → Secrets and variables → Actions
2. Add:
   - `RENDER_API_KEY`: Get from Render dashboard
   - `VERCEL_TOKEN`: Get from Vercel account settings

---

## Step 9: Setup Monitoring (Free)

### 9.1 Sentry error tracking (free)

```bash
# Sign up at https://sentry.io (free tier: 5k errors/month)

# Get DSN from Sentry project settings
# Add to Render environment:
SENTRY_DSN=https://key@sentry.io/project-id
```

Update **backend/main.py**:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
)
```

### 9.2 Uptime monitoring (free)

Use https://uptime.kuma.pet (self-hosted) or https://status.io (free tier)

Monitor endpoints:
- Backend: `https://floodguard-backend.onrender.com/health`
- Frontend: `https://floodguard-ke.vercel.app`

---

## Step 10: Setup Email Alerts (Free)

### 10.1 SendGrid free tier

```bash
# Sign up at https://sendgrid.com (free: 100 emails/day)

# Get API key, add to Render:
SENDGRID_API_KEY=SG.xxx
```

Update **backend/services/email.py**:
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_alert_email(to, subject, body):
    sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
    message = Mail(
        from_email='noreply@floodguard.ke',
        to_emails=to,
        subject=subject,
        html_content=body,
    )
    sg.send(message)
```

---

## Deployment Checklist

- [ ] GitHub repo created + code pushed
- [ ] Neon PostgreSQL database created + migrations run
- [ ] Upstash Redis database created
- [ ] Render backend deployed (`/health` returns 200)
- [ ] Vercel frontend deployed (loads without errors)
- [ ] Environment variables set in Render
- [ ] Frontend can call backend API
- [ ] Sentry error tracking working
- [ ] CI/CD pipeline configured
- [ ] Android APK built + uploaded to GitHub Releases

---

## Cost Breakdown (Monthly)

| Service | Free Tier | Usage | Cost |
|---------|-----------|-------|------|
| **Neon PostgreSQL** | 3GB storage, 5 conn | ~500MB | $0 |
| **Upstash Redis** | 10k commands/day | ~5k/day | $0 |
| **Render Backend** | 512MB, auto-sleep | Always on | $0* |
| **Vercel Frontend** | Unlimited | ~100GB bandwidth | $0 |
| **Sentry** | 5k errors/month | ~2k errors | $0 |
| **SendGrid** | 100 emails/day | ~50/day | $0 |
| **GitHub** | Unlimited repos | 1 repo | $0 |
| **TOTAL** | | | **$0/month** |

*Render free tier auto-sleeps after 15 min → 10-30s cold start. Upgrade to $7/month ($0.10/hour) to always run.

---

## Limitations of Free Tier

| Feature | Limitation | Workaround |
|---------|-----------|-----------|
| **Backend cold start** | 10-30s after inactivity | Upgrade to paid ($7/month) |
| **Database connections** | 5 concurrent | Use connection pooling (PgBouncer) |
| **Redis commands** | 10k/day | Cache selectively |
| **Email** | 100/day | Use SMS (Africa's Talking free trial) |
| **Storage** | 1GB (Render) | Use Cloudinary free tier (25GB) |
| **Bandwidth** | Unmetered (Vercel) | ✓ OK for Kenya traffic |

---

## Scaling to Paid (When You Need It)

### Estimated costs for 100k users:

| Component | Free → Paid |
|-----------|-----------|
| Render Backend | $0 → $50/month (512MB → 2GB) |
| Neon PostgreSQL | $0 → $50/month (3GB → 50GB) |
| Upstash Redis | $0 → $30/month (unlimited commands) |
| Vercel Pro | $0 → $20/month (priority support) |
| Sentry | $0 → $29/month (50k errors) |
| SendGrid SMS | $0 → $100/month (10M SMS) |
| **TOTAL** | **$0 → $279/month** |

---

## Testing Your Deployment

### 1. Test Backend Health

```bash
curl https://floodguard-backend.onrender.com/health
# Should return: {"status": "ok"}
```

### 2. Test Database Connection

```bash
curl https://floodguard-backend.onrender.com/risk/KEN01
# Should return risk data for Nairobi
```

### 3. Test Frontend

Open https://floodguard-ke.vercel.app in browser
- Dashboard should load
- Map should show Kenya counties
- Click county → risk details appear

### 4. Test API from Frontend

Open browser → F12 (DevTools) → Network tab
- Click on network request to `/risk/KEN01`
- Should see 200 response with JSON

---

## Troubleshooting

### Backend won't deploy on Render

**Error**: `ModuleNotFoundError`
**Fix**: Make sure `requirements.txt` has all dependencies:
```bash
pip freeze > backend/requirements.txt
git push
```

### Frontend showing 404 on API calls

**Error**: `Failed to fetch from https://floodguard-backend.onrender.com`
**Fix**: Check that `NEXT_PUBLIC_API_URL` is set in Vercel environment

### Database migrations failed

**Error**: `Alembic head is not set`
**Fix**: Run manually:
```bash
cd backend
export DATABASE_URL="postgresql://..."
alembic upgrade head
```

### Redis connection timeout

**Error**: `ConnectionRefusedError` from Upstash
**Fix**: Check that `REDIS_URL` is correct format:
```
redis://default:password@host:port
```

### Cold start too slow (Render)

**Error**: First request after 15 min takes 30s
**Solution**: Upgrade to paid ($7/month) OR keep backend "warm" with cron job:
```bash
# Add to GitHub Actions (runs every 10 min)
- name: Keep backend warm
  run: curl https://floodguard-backend.onrender.com/health
  
# Schedule: 0 */10 * * * *
```

---

## Next Steps

1. **Deploy locally first** to test everything works
2. **Push to GitHub** to track all changes
3. **Deploy to Render** (backend)
4. **Deploy to Vercel** (frontend)
5. **Monitor in Sentry** for errors
6. **Add CI/CD** for auto-deployments
7. **Scale to paid** when you reach free tier limits

---

## Resources

- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [Neon Docs](https://neon.tech/docs)
- [Upstash Docs](https://upstash.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Deployment](https://nextjs.org/learn/basics/deploying-nextjs-app)

---

**You now have a fully functional flood warning system running completely free!** 🎉

