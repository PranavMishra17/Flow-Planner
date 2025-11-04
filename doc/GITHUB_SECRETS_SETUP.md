# GitHub Secrets Setup Guide

Guide for adding API keys to GitHub repository for CI/CD workflows.

---

## 🔐 Required Secrets

Your GitHub Actions workflows need these secrets to run tests:

| Secret Name | Description | Where to Get It |
|-------------|-------------|-----------------|
| **GEMINI_API_KEY** | Google Gemini API key | https://aistudio.google.com/app/apikey |
| **ANTHROPIC_API_KEY** | Anthropic Claude API key | https://console.anthropic.com/ |
| **SECRET_KEY** | Flask secret (optional) | Generate with Python (see below) |

---

## 📝 Step-by-Step Setup

### Step 1: Get Your API Keys

#### 1.1 Google Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the generated key (starts with `AIza...`)
4. **Save it securely** - you'll need it in Step 2

#### 1.2 Anthropic Claude API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the generated key (starts with `sk-ant-...`)
6. **Save it securely** - you'll need it in Step 2

#### 1.3 Generate Flask SECRET_KEY (Optional)
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output (64 character hex string)

---

### Step 2: Add Secrets to GitHub

#### Via GitHub Web Interface

1. **Go to your repository on GitHub**
   ```
   https://github.com/YourUsername/Flow-Planner
   ```

2. **Click on "Settings" tab** (top right)

3. **In left sidebar, click:**
   - "Secrets and variables" → "Actions"

4. **Click "New repository secret"** (green button)

5. **Add each secret one by one:**

   **Secret #1: GEMINI_API_KEY**
   ```
   Name: GEMINI_API_KEY
   Value: [paste your Gemini API key here]
   ```
   Click "Add secret"

   **Secret #2: ANTHROPIC_API_KEY**
   ```
   Name: ANTHROPIC_API_KEY
   Value: [paste your Claude API key here]
   ```
   Click "Add secret"

   **Secret #3: SECRET_KEY (optional)**
   ```
   Name: SECRET_KEY
   Value: [paste generated secret key here]
   ```
   Click "Add secret"

6. **Verify secrets are added:**
   - You should see all 3 secrets listed
   - Values will be hidden (shown as `***`)

---

### Step 3: Verify Setup

#### Test Locally First

```bash
# Set environment variables locally
export GEMINI_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"
export SECRET_KEY="your_secret_here"

# Run tests
pytest tests/test_deployment.py::TestAPIConnectivity -v
```

#### Push to GitHub to Trigger CI

```bash
git add .
git commit -m "Add GitHub Actions secrets"
git push origin main
```

#### Check GitHub Actions

1. Go to "Actions" tab in your repository
2. Click on the latest workflow run
3. Check if tests pass:
   - ✅ Green checkmark = Success
   - ❌ Red X = Failed (check logs)

---

## 🔍 Troubleshooting

### Issue: Secrets Not Working in Actions

**Symptoms:**
- Tests fail with "API key not set"
- Workflow shows `***` but tests don't run

**Solutions:**

1. **Verify secret names match exactly:**
   ```yaml
   # In .github/workflows/code-quality.yml
   env:
     GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}    # Must match!
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # Must match!
   ```

2. **Check secret values:**
   - No leading/trailing spaces
   - Complete key copied
   - Not expired

3. **Re-create secrets:**
   - Delete old secret
   - Add new secret with correct value

### Issue: API Tests Timeout

**Cause:** API rate limits or network issues

**Solution:**
```bash
# Run tests with longer timeout
pytest tests/test_deployment.py --timeout=60
```

### Issue: Tests Pass Locally but Fail in CI

**Cause:** Environment differences

**Solution:**
1. Check Python version matches (3.11)
2. Verify all dependencies in `requirements.txt`
3. Check GitHub Actions logs for details

---

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Use GitHub Secrets for all sensitive data
- ✅ Rotate API keys regularly
- ✅ Use different keys for production vs testing
- ✅ Set API key spending limits
- ✅ Monitor API usage

### ❌ DON'T:
- ❌ Commit API keys to git
- ❌ Share API keys in pull requests
- ❌ Log API keys in console
- ❌ Use production keys for testing
- ❌ Store keys in code comments

---

## 📊 Checking Secret Usage

### View Secret Usage in Workflow

Secrets are accessed in workflows like this:

```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

### Verify Secrets Are Set (Without Revealing Values)

Add this temporary step to your workflow:

```yaml
- name: Check secrets
  run: |
    if [ -z "$GEMINI_API_KEY" ]; then
      echo "❌ GEMINI_API_KEY not set"
    else
      echo "✅ GEMINI_API_KEY is set"
    fi
```

---

## 🔄 Updating Secrets

### When to Update:
- API key compromised
- Key expired
- Key rotation policy
- Switching to different account

### How to Update:

1. **Go to:** Settings → Secrets and variables → Actions
2. **Click on the secret name**
3. **Click "Update secret"**
4. **Enter new value**
5. **Click "Update secret"**

Changes take effect immediately for new workflow runs.

---

## 🎯 Quick Reference

```bash
# Get Gemini API Key
https://aistudio.google.com/app/apikey

# Get Claude API Key
https://console.anthropic.com/

# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Add to GitHub
Repository → Settings → Secrets and variables → Actions → New repository secret

# Test locally
pytest tests/test_deployment.py::TestAPIConnectivity -v

# Check GitHub Actions
Repository → Actions tab → Latest run
```

---

## 📞 Need Help?

- **GitHub Actions Docs:** https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Testing Guide:** [TESTING.md](TESTING.md)
- **Deployment Guide:** [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)

---

**Secrets configured? → Run `git push` and watch your tests pass! ✅**
