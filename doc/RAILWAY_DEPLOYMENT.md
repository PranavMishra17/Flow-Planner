# Railway Deployment Guide

Complete guide for deploying Flow Planner to Railway.app with full functionality.

## ✅ Why Railway?

Railway is the **best platform** for this application because it supports:

- ✅ **WebSockets** - Real-time SocketIO connections for live logs
- ✅ **Long-running processes** - Background workflow execution
- ✅ **Browser automation** - Playwright/Browser-Use support
- ✅ **Persistent storage** - File uploads and screenshots
- ✅ **Easy deployment** - GitHub integration with auto-deploy
- 💰 **Free tier** - $5/month credit (plenty for hobby projects)

---

## 🚀 Quick Deploy (5 Minutes)

### Step 1: Access Railway

Go to your project: https://railway.com/project/9b2e9d9a-97e6-4dff-983f-a3704e680083

Or create a new project: https://railway.app/new

### Step 2: Create Service

1. Click **"+ New"** button
2. Select **"GitHub Repo"**
3. Authorize GitHub if needed
4. Select **"Flow-Planner"** repository
5. Click **"Deploy Now"**

### Step 3: Add Environment Variables

Click on your service → **"Variables"** tab → **"+ New Variable"**

Add these variables:

```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_claude_api_key_here
SECRET_KEY=<generate-random-secret-see-below>
PORT=5000
FLASK_ENV=production
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste as `SECRET_KEY` value.

### Step 4: Generate Domain

1. Go to **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. Your app will be live at: `https://flow-planner-production-XXXX.railway.app`

### Step 5: Monitor Deployment

- Click **"Deployments"** tab to see build progress
- Click **"View Logs"** to see deployment logs
- Build takes ~5-10 minutes (installs Playwright browsers)

---

## 🔧 Configuration Files

All necessary files are already included:

### `railway.json` (Already created)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt && playwright install chromium"
  },
  "deploy": {
    "startCommand": "python app.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### `Procfile` (Already created)
```
web: python app.py
```

### `requirements.txt` (Already exists)
Includes all dependencies for full functionality.

---

## 📦 Optional: Environment Variables

You can add these optional variables for advanced configuration:

```bash
# Browser Configuration
HEADLESS_BROWSER=True              # Run browser headless (default: True)
USE_PERSISTENT_CONTEXT=False       # Save browser session (default: False)

# Refinement Configuration
ENABLE_REFINEMENT=True             # Enable vision refinement (default: True)
REFINEMENT_AUTO=True               # Auto-run refinement (default: True)
REFINEMENT_MODEL=claude-sonnet-4   # Primary model (default: claude-sonnet-4)
REFINEMENT_FALLBACK=claude-sonnet-4 # Fallback model

# Debug (use only for troubleshooting)
DEBUG=False                        # NEVER set to True in production
```

---

## 🔄 Auto-Deploy with GitHub Actions

Enable automatic deployments when you push to GitHub:

### Railway automatically deploys on:
- ✅ Push to `main` branch
- ✅ Pull request merges
- ✅ Manual redeploys

### Disable auto-deploy (if needed):
1. Go to **"Settings"** → **"Service"**
2. Toggle **"Auto Deploy"** off

---

## 📊 Monitoring & Logs

### View Real-time Logs

**Web Dashboard:**
1. Click your service
2. Click **"View Logs"** button
3. Logs stream in real-time

**CLI:**
```bash
railway logs
railway logs --follow  # Stream logs
```

### Check Deployment Status

```bash
railway status
```

### View Metrics

1. Go to **"Metrics"** tab
2. See CPU, memory, network usage
3. Monitor request counts and response times

---

## 🐛 Troubleshooting

### Issue: Build fails with "Out of memory"

**Solution:** Upgrade to Railway Pro ($20/month) for more memory, or optimize build:

```bash
# In railway.json, add memory limit
"deploy": {
  "startCommand": "python app.py",
  "memoryLimit": 2048
}
```

### Issue: Playwright browsers not installing

**Solution:** Check build logs. If needed, manually trigger install:

```bash
# Add to railway.json buildCommand
"buildCommand": "pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium"
```

### Issue: Environment variables not loading

**Solution:**
1. Go to **"Variables"** tab
2. Verify all variables are set
3. Click **"Redeploy"** after adding variables

### Issue: App crashes immediately

**Check logs for:**
```bash
railway logs
```

Common causes:
- Missing environment variables (GEMINI_API_KEY, ANTHROPIC_API_KEY)
- Port binding issue (make sure PORT=5000 is set)
- Database connection failures

### Issue: WebSocket connections fail

**Solution:** Railway automatically supports WebSockets. If failing:
1. Check firewall/proxy settings on client side
2. Verify SocketIO version matches client and server
3. Check browser console for errors

---

## 🔐 Security Best Practices

### 1. Never commit secrets
```bash
# .gitignore already includes:
.env
*.key
*.pem
```

### 2. Rotate API keys regularly
Update Railway variables:
1. **"Variables"** tab → Edit variable
2. Update value
3. Click **"Redeploy"**

### 3. Use strong SECRET_KEY
Generate new key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Enable HTTPS (automatic)
Railway provides automatic HTTPS for all domains.

### 5. Set FLASK_ENV=production
Never use `DEBUG=True` in production.

---

## 💰 Pricing & Usage

### Free Tier ($5/month credit)
- Enough for hobby projects and demos
- ~500 hours of runtime per month
- Includes all features

### Pro Plan ($20/month)
- Unlimited projects
- More memory and CPU
- Priority support

### Monitor Usage
1. Go to **"Usage"** in dashboard
2. See credit consumption
3. Set up billing alerts

---

## 🌐 Custom Domain

### Add Custom Domain

1. Go to **"Settings"** → **"Networking"**
2. Click **"Custom Domain"**
3. Enter your domain: `flowplanner.yourdomain.com`
4. Add CNAME record to your DNS:
   ```
   CNAME flowplanner.yourdomain.com → your-app.railway.app
   ```
5. Wait for DNS propagation (5-30 minutes)

### SSL Certificate
Railway automatically provisions SSL certificates for custom domains.

---

## 🔄 Updating Your App

### Via Git Push (Automatic)
```bash
git add .
git commit -m "Update app"
git push origin main
```
Railway auto-deploys in ~5 minutes.

### Via Railway Dashboard (Manual)
1. Click **"Deployments"** tab
2. Click **"Redeploy"**

### Rollback to Previous Version
1. Click **"Deployments"** tab
2. Find previous successful deployment
3. Click **"..."** → **"Redeploy"**

---

## 📝 Health Checks

Railway automatically monitors your app's health.

### Custom Health Endpoint
Your app includes:
```
GET /api/health
```

Returns:
```json
{
  "status": "online",
  "timestamp": "2025-11-04T12:34:56Z"
}
```

Railway pings this endpoint to verify app is running.

---

## 🚨 Alerts & Notifications

### Set Up Alerts

1. Go to **"Settings"** → **"Notifications"**
2. Connect Slack, Discord, or Email
3. Configure alerts for:
   - Deployment failures
   - App crashes
   - High memory usage

---

## 🎯 Performance Optimization

### 1. Enable Caching
Railway includes Redis addon:
```bash
railway add redis
```

### 2. Optimize Build Time
Cache dependencies:
```json
{
  "build": {
    "buildCommand": "pip install --cache-dir .pip-cache -r requirements.txt"
  }
}
```

### 3. Reduce Image Size
Use slim Python image (already optimized in Nixpacks).

### 4. Monitor Performance
- Check **"Metrics"** tab regularly
- Optimize slow endpoints
- Enable logging for debugging

---

## 📞 Support

### Railway Support
- Documentation: https://docs.railway.app
- Discord: https://discord.gg/railway
- Twitter: @Railway

### App-Specific Issues
- Check GitHub repository issues
- Review logs: `railway logs`
- Enable debug logging (temporarily)

---

## ✅ Post-Deployment Checklist

After deployment, verify:

- [ ] App loads at Railway URL
- [ ] Health endpoint returns 200: `/api/health`
- [ ] Environment variables are set
- [ ] Can create new workflow
- [ ] Live logs appear in real-time
- [ ] Browser automation works
- [ ] Workflow guide generates successfully
- [ ] Refinement feature works (if enabled)

---

## 🎉 Your App is Live!

Your Flow Planner is now deployed with full functionality:
- ✅ Real-time workflow execution
- ✅ Browser automation
- ✅ AI-powered guide generation
- ✅ Vision-based refinement
- ✅ WebSocket live updates

Share your Railway URL and start capturing workflows! 🚀

---

## 📚 Additional Resources

- **Railway Docs:** https://docs.railway.app
- **Railway CLI:** https://docs.railway.app/develop/cli
- **Playwright Docs:** https://playwright.dev/python/
- **Flask-SocketIO:** https://flask-socketio.readthedocs.io/
- **Browser-Use:** https://github.com/browser-use/browser-use

---

**Questions?** Check the Railway Discord or open an issue on GitHub.
