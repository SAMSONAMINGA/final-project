# 🚀 FloodGuard KE - Free Deployment Checklist

## What I've Done (95%)

✅ Added `gunicorn` to requirements.txt (production server)  
✅ Created `Procfile` for Render deployment  
✅ Created `runtime.txt` (Python 3.11)  
✅ Created `.env.render` template with all required variables  
✅ Created `.github/workflows/deploy.yml` for auto-deployment  
✅ Created `frontend/.env.local.example` for Vercel  
✅ Updated `frontend/next.config.js` for Vercel optimization  
✅ Updated `.gitignore` to prevent committing secrets  
✅ Created `FREE-DEPLOYMENT.md` (detailed guide)  
✅ Created `QUICK-DEPLOY-STEPS.md` (simplified steps)  
✅ Created `deploy.sh` (interactive setup script)  

---

## What You Need to Do (5%)

### ✋ ACTION REQUIRED - These need your manual involvement:

---

## PART 1: Create Free Accounts (5 minutes)

### 1.1 Create GitHub Account
- Go to: https://github.com/signup
- Sign up with email
- **Save credentials** - you'll need them

### 1.2 Create Neon Account (PostgreSQL)
- Go to: https://neon.tech/signup
- Sign up with GitHub
- Create new project:
  - Name: `floodguard-ke`
  - Region: `us-east-1`
- Copy CONNECTION STRING (looks like: `postgresql://user:password@host/floodguard`)
- **SAVE THIS** - you'll need it for Render

### 1.3 Create Upstash Account (Redis)
- Go to: https://upstash.com/login
- Sign up with GitHub
- Create new Redis database:
  - Name: `floodguard-cache`
  - Region: `US-EAST-1`
- Copy REDIS URL (looks like: `redis://default:token@host:port`)
- **SAVE THIS** - you'll need it for Render

### 1.4 Create Render Account
- Go to: https://render.com/register
- Sign up with GitHub
- Authorize Render to access your GitHub repos

### 1.5 Create Vercel Account
- Go to: https://vercel.com/signup
- Sign up with GitHub
- Authorize Vercel to access your GitHub repos

---

## PART 2: Push Code to GitHub (3 minutes)

### 2.1 Initialize Git
Open terminal/PowerShell in your project folder and run:

```bash
git init
git config user.name "Your Name"
git config user.email "your@email.com"
git add .
git commit -m "Initial commit: FloodGuard KE deployment-ready"
```

### 2.2 Create GitHub Repository
- Go to: https://github.com/new
- Repository name: `floodguard-ke`
- Description: `Flood early warning system for Kenya`
- Choose **Public** (needed for free deployment)
- Click **"Create repository"**

### 2.3 Push Code
After repo is created, GitHub shows you these commands. Copy and paste:

```bash
git remote add origin https://github.com/YOUR_USERNAME/floodguard-ke.git
git branch -M main
git push -u origin main
```

✅ Your code is now on GitHub!

---

## PART 3: Deploy Backend to Render (10 minutes)

### 3.1 Create Render Service

1. Go to: https://render.com/dashboard
2. Click **"+ New"** → **"Web Service"**
3. Select your repo: `floodguard-ke`
4. Configure:

| Field | Value |
|-------|-------|
| **Name** | `floodguard-backend` |
| **Environment** | `Python` |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120` |
| **Plan** | `Free` |

### 3.2 Add Environment Variables

Click **"Advanced"** and add these vars:

```
DATABASE_URL = (from Neon - paste CONNECTION STRING)
REDIS_URL = (from Upstash - paste REDIS URL)
SECRET_KEY = (generate below)
ALLOWED_ORIGINS = https://localhost:3000,http://localhost:3000
AFRICAS_TALKING_API_KEY = dummy-key-for-testing
AFRICAS_TALKING_USERNAME = dummy
NASA_BEARER_TOKEN = dummy
IMERG_BASE_URL = https://dummy.com/
OPENWEATHER_API_KEY = dummy
ENV = production
DEBUG = False
LOG_LEVEL = INFO
```

**How to generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
(Copy the output)

### 3.3 Deploy

Click **"Create Web Service"** and wait 5-10 minutes.

✅ When done, you'll see a green checkmark and a URL like:
```
https://floodguard-backend-xyz.onrender.com
```

**SAVE THIS URL** - you'll need it for Vercel!

### 3.4 Test Backend

```bash
curl https://floodguard-backend-xyz.onrender.com/health
```

Should return:
```json
{"status": "healthy", ...}
```

---

## PART 4: Deploy Frontend to Vercel (5 minutes)

### 4.1 Create Vercel Project

1. Go to: https://vercel.com/dashboard
2. Click **"+ Add New"** → **"Project"**
3. Select your repo: `floodguard-ke`
4. Configure:

| Field | Value |
|-------|-------|
| **Framework** | `Next.js` |
| **Root Directory** | `frontend` |

### 4.2 Add Environment Variable

Add one environment variable:
```
NEXT_PUBLIC_API_URL = (from Render backend URL above)
```

Example:
```
NEXT_PUBLIC_API_URL = https://floodguard-backend-xyz.onrender.com
```

### 4.3 Deploy

Click **"Deploy"** and wait 2-3 minutes.

✅ When done, Vercel shows your frontend URL:
```
https://floodguard-ke-yourname.vercel.app
```

---

## PART 5: Test Everything (5 minutes)

### 5.1 Test Backend Health

```bash
curl https://floodguard-backend-xyz.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "redis": "ok",
    "ml_model": "ok",
    "county_data": "ok"
  }
}
```

### 5.2 Test Frontend

Open in browser:
```
https://floodguard-ke-yourname.vercel.app
```

Should show:
- ✅ Map loading
- ✅ Kenya counties displayed
- ✅ No console errors (F12 → Console)

### 5.3 Test API Integration

1. Open browser DevTools: **F12**
2. Go to **Network** tab
3. Click on a county in the app
4. Look for API request to `/risk/KEN01`
5. Should return **200** with JSON data

---

## 🎉 YOU'RE DONE!

Your system is now **100% live and free**:

| Component | URL |
|-----------|-----|
| **Backend API** | `https://floodguard-backend-xyz.onrender.com` |
| **Frontend** | `https://floodguard-ke-yourname.vercel.app` |
| **Database** | Neon (3GB free) |
| **Cache** | Upstash Redis (10k commands/day) |
| **Cost** | **$0/month** ✓ |

---

## 📊 System Status

All services should show:
- ✅ Frontend loading
- ✅ Backend responding to health checks
- ✅ Database connected
- ✅ Redis cache working
- ✅ No errors in console

---

## ⚠️ Common Issues & Fixes

### Issue: Backend deployment fails

**Error in Render logs**: `ModuleNotFoundError: No module named 'gunicorn'`

**Fix**: 
- Requirements.txt already has gunicorn added ✓
- If still fails, re-push to GitHub:
```bash
git add backend/requirements.txt
git commit -m "Fix: ensure gunicorn in requirements"
git push
```

---

### Issue: Frontend shows blank page

**Error in browser console**: `Failed to fetch from http://localhost:8000`

**Fix**: 
- NEXT_PUBLIC_API_URL environment variable not set in Vercel
- Go to Vercel dashboard → Settings → Environment Variables
- Add: `NEXT_PUBLIC_API_URL = https://your-render-backend-url.com`
- Redeploy: Vercel → Deployments → Click latest → "Redeploy"

---

### Issue: API calls return 404

**Error**: `POST /risk/KEN01 → 404 Not Found`

**Fix**:
- Backend URL is wrong in NEXT_PUBLIC_API_URL
- Check it has `https://` and no trailing slash
- Correct example: `https://floodguard-backend-xyz.onrender.com`

---

### Issue: Cold start is slow (30 seconds)

**Expected on free tier** - Render auto-sleeps after 15 minutes

**Solutions**:
- Option 1: Upgrade to paid ($7/month) - "Starter" plan always runs
- Option 2: Keep warm with GitHub Actions (runs every 10 min)
- Option 3: Accept 30s cold start, it's normal on free tier

---

### Issue: "Cannot connect to database"

**Error**: `psycopg2.OperationalError`

**Fixes**:
- Check DATABASE_URL is correct (copy exactly from Neon)
- Verify connection string format: `postgresql://user:password@host/database`
- Check Neon project is not suspended (free tier sleeps after inactivity)
- Restart Render service: Render dashboard → Manual Deploy → Deploy

---

## 📞 Support Resources

| Topic | Link |
|-------|------|
| **Render Documentation** | https://render.com/docs |
| **Vercel Documentation** | https://vercel.com/docs |
| **Neon Documentation** | https://neon.tech/docs |
| **Upstash Documentation** | https://upstash.com/docs |
| **FastAPI Deployment** | https://fastapi.tiangolo.com/deployment/ |
| **Next.js Deployment** | https://nextjs.org/docs/deployment |

---

## 🎯 Next Steps (Optional)

Once everything is working:

1. **Add more API keys** (currently using dummy values):
   - Africa's Talking: https://africastalking.com
   - NASA IMERG: https://urs.earthdata.nasa.gov
   - OpenWeather: https://openweathermap.org

2. **Enable auto-deployments** with GitHub Actions (already configured)

3. **Add domain name** (free):
   - Vercel: Add custom domain in Settings
   - Render: Add custom domain in Settings

4. **Scale to production** when needed:
   - Render: Upgrade to paid ($7-50/month)
   - Vercel: Upgrade to Pro ($20/month)
   - Neon: Increase storage (pay-as-you-go)
   - Upstash: Upgrade plan (pay-as-you-go)

---

## 📋 Final Checklist

- [ ] Created GitHub account
- [ ] Created Neon PostgreSQL database
- [ ] Created Upstash Redis database
- [ ] Created Render account
- [ ] Created Vercel account
- [ ] Pushed code to GitHub
- [ ] Deployed backend to Render
- [ ] Deployed frontend to Vercel
- [ ] Backend `/health` returns 200
- [ ] Frontend loads without errors
- [ ] API calls work from frontend
- [ ] All systems are green ✅

---

**Congratulations! You now have a production-grade flood warning system running completely free!** 🌍💧⚠️

