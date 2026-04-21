# FloodGuard KE - Deploy in 30 Minutes (Free)

I've prepared 95% of the deployment. You just need to do these **4 manual steps**:

---

## STEP 1: Create Free Accounts (5 min)

Go to each and sign up with GitHub (easiest):

1. **Neon** (PostgreSQL): https://neon.tech
   - Create project → copy connection string
   - Save as: `DATABASE_URL`

2. **Upstash** (Redis): https://upstash.com
   - Create database → copy Redis URL
   - Save as: `REDIS_URL`

3. **Render** (Backend hosting): https://render.com
   - Connect GitHub account

4. **Vercel** (Frontend hosting): https://vercel.com
   - Connect GitHub account

---

## STEP 2: Push Code to GitHub (3 min)

```bash
# Initialize git (if not done)
git init
git config user.name "Your Name"
git config user.email "your@email.com"

git add .
git commit -m "Initial commit: FloodGuard KE deployment-ready"

# Create repo on GitHub.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/floodguard-ke.git
git branch -M main
git push -u origin main
```

**Your repo is now public at**: `https://github.com/YOUR_USERNAME/floodguard-ke`

---

## STEP 3: Deploy Backend to Render (10 min)

1. Go to https://render.com → Dashboard
2. Click **"New +"** → **"Web Service"**
3. Select your GitHub repo: `floodguard-ke`
4. Configure:
   - **Name**: `floodguard-backend`
   - **Environment**: `Python`
   - **Build command**: `pip install -r backend/requirements.txt`
   - **Start command**: `cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - **Plan**: `Free`
5. Click **"Advanced"** and add **Environment Variables**:

```
DATABASE_URL = (paste from Neon)
REDIS_URL = (paste from Upstash)
SECRET_KEY = (run: python -c "import secrets; print(secrets.token_urlsafe(32))")
ALLOWED_ORIGINS = https://YOUR_VERCEL_URL.vercel.app,https://localhost:3000
AFRICAS_TALKING_API_KEY = test-key
AFRICAS_TALKING_USERNAME = test
NASA_BEARER_TOKEN = test
IMERG_BASE_URL = https://test.com/
OPENWEATHER_API_KEY = test
ENV = production
DEBUG = False
LOG_LEVEL = INFO
```

6. Click **"Create Web Service"**
7. Wait 5-10 minutes for deployment
8. Copy backend URL: `https://floodguard-backend-xyz.onrender.com`

---

## STEP 4: Deploy Frontend to Vercel (5 min)

1. Go to https://vercel.com → Dashboard
2. Click **"Add New"** → **"Project"**
3. Import your GitHub repo: `floodguard-ke`
4. Configure:
   - **Framework**: Next.js
   - **Root Directory**: `frontend`
5. Add **Environment Variable**:

```
NEXT_PUBLIC_API_URL = (paste your Render backend URL from Step 3)
```

6. Click **"Deploy"**
7. Wait 2-3 minutes
8. Your frontend is live at: `https://floodguard-ke-YOUR_VERCEL_ACCOUNT.vercel.app`

---

## Done! 🎉

Your system is now **100% live and free**:

- **Backend**: https://floodguard-backend-xyz.onrender.com
- **Frontend**: https://floodguard-ke-xxx.vercel.app
- **Database**: Neon (3GB free)
- **Cache**: Upstash Redis (free)
- **Cost**: **$0/month** ✓

---

## Next: Test It Works

### 1. Test backend health
```bash
curl https://floodguard-backend-xyz.onrender.com/health
# Should return: {"status": "healthy", ...}
```

### 2. Test frontend
Open in browser: `https://floodguard-ke-xxx.vercel.app`
- Map should load
- Counties should display

### 3. Test API call from frontend
Open browser DevTools (F12) → Network tab
- Click on county
- Should see API call to `/risk/KEN01`
- Should return 200 with JSON

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't deploy | Check logs in Render → Logs. Usually missing env var |
| "Cannot find module" error | Make sure requirements.txt has gunicorn |
| Frontend shows blank | Check NEXT_PUBLIC_API_URL is set correctly |
| API calls return 404 | Backend URL is wrong. Check both have https:// |
| Cold start too slow | Normal on free tier. Upgrade to $7/month if needed |

---

## Files I Created

- `backend/requirements.txt` - Added gunicorn
- `backend/Procfile` - Render deployment config
- `backend/runtime.txt` - Python version
- `backend/.env.render` - Environment template
- `backend/render.yaml` - Alternative Render config
- `frontend/.env.local.example` - Vercel env template
- `frontend/next.config.js` - Optimization for Vercel
- `.github/workflows/deploy.yml` - Auto-deploy on git push
- `.gitignore` - Prevent committing secrets
- `FREE-DEPLOYMENT.md` - Full detailed guide
- `QUICK-DEPLOY-STEPS.md` - This file

---

**Questions?** Check FREE-DEPLOYMENT.md for detailed explanations.

