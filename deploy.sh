#!/bin/bash
# Quick deployment helper script
# Automates git setup + provides step-by-step prompts

set -e

echo "=========================================="
echo "FloodGuard KE - Free Deployment Setup"
echo "=========================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Install from https://git-scm.com/"
    exit 1
fi

# Step 1: Git setup
echo "📝 STEP 1: Git Configuration"
echo "----------------------------------------"
read -p "Your name: " git_name
read -p "Your email: " git_email

git config user.name "$git_name"
git config user.email "$git_email"

# Step 2: Initialize git
if [ ! -d ".git" ]; then
    echo "🔧 Initializing git repository..."
    git init
    git branch -M main
    git add .
    git commit -m "Initial commit: FloodGuard KE deployment-ready

Assisted-By: Gordon"
else
    echo "✓ Git already initialized"
fi

# Step 3: GitHub info
echo ""
echo "🌐 STEP 2: GitHub Repository"
echo "----------------------------------------"
read -p "GitHub username: " github_username
repo_url="https://github.com/$github_username/floodguard-ke.git"

echo "Repository URL: $repo_url"
echo ""
echo "⚠️  IMPORTANT:"
echo "1. Go to https://github.com/new"
echo "2. Create repo named: floodguard-ke"
echo "3. Copy the repo URL above"
echo "4. Come back and I'll push code"
echo ""
read -p "Ready to push? (y/n): " ready

if [ "$ready" = "y" ]; then
    git remote add origin "$repo_url" 2>/dev/null || git remote set-url origin "$repo_url"
    git push -u origin main
    echo "✓ Code pushed to GitHub!"
fi

# Step 4: API keys
echo ""
echo "🔑 STEP 3: Get API Keys"
echo "----------------------------------------"
echo "You'll need these credentials from:"
echo ""
echo "1. Neon (PostgreSQL)"
echo "   - Go to: https://neon.tech"
echo "   - Sign up → Create project"
echo "   - Copy CONNECTION STRING (looks like: postgresql://...)"
echo ""
read -p "Paste DATABASE_URL here: " database_url

echo ""
echo "2. Upstash (Redis)"
echo "   - Go to: https://upstash.com"
echo "   - Create Redis database"
echo "   - Copy REDIS_URL from dashboard"
echo ""
read -p "Paste REDIS_URL here: " redis_url

# Step 5: Generate secret key
echo ""
echo "🔐 STEP 4: Generate Security Key"
echo "----------------------------------------"
secret_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated SECRET_KEY: $secret_key"

# Step 6: Display Render setup
echo ""
echo "🚀 STEP 5: Deploy Backend"
echo "----------------------------------------"
echo "1. Go to: https://render.com"
echo "2. Sign up with GitHub"
echo "3. Click 'New +' → 'Web Service'"
echo "4. Connect GitHub repo: floodguard-ke"
echo "5. Configure:"
echo "   - Name: floodguard-backend"
echo "   - Environment: Python"
echo "   - Build command: pip install -r backend/requirements.txt"
echo "   - Start command: cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$PORT --timeout 120"
echo "   - Plan: Free"
echo ""
echo "6. Click 'Advanced' and add these env vars:"
cat << EOF

DATABASE_URL=$database_url
REDIS_URL=$redis_url
SECRET_KEY=$secret_key
ALLOWED_ORIGINS=https://YOUR_VERCEL_URL.vercel.app,http://localhost:3000
AFRICAS_TALKING_API_KEY=test
AFRICAS_TALKING_USERNAME=test
NASA_BEARER_TOKEN=test
IMERG_BASE_URL=https://test.com/
OPENWEATHER_API_KEY=test
ENV=production
DEBUG=False
LOG_LEVEL=INFO

EOF

echo "7. Click 'Create Web Service' and wait 5-10 minutes"
echo "8. Copy your backend URL when ready"
echo ""
read -p "Enter backend URL (e.g., https://floodguard-backend-xyz.onrender.com): " backend_url

# Step 7: Display Vercel setup
echo ""
echo "🎨 STEP 6: Deploy Frontend"
echo "----------------------------------------"
echo "1. Go to: https://vercel.com"
echo "2. Sign up with GitHub"
echo "3. Click 'Add New' → 'Project'"
echo "4. Import your repo: floodguard-ke"
echo "5. Configure:"
echo "   - Framework: Next.js"
echo "   - Root Directory: frontend"
echo ""
echo "6. Add environment variable:"
echo "   NEXT_PUBLIC_API_URL=$backend_url"
echo ""
echo "7. Click 'Deploy' and wait 2-3 minutes"
echo ""

# Step 8: Test
echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Your system is now live:"
echo "  Backend:  $backend_url"
echo "  Frontend: Check Vercel dashboard for URL"
echo ""
echo "Next, test it works:"
echo "  1. curl $backend_url/health"
echo "  2. Open frontend in browser"
echo "  3. Check DevTools Network tab for API calls"
echo ""
echo "For help, see: QUICK-DEPLOY-STEPS.md"
echo ""
