# Testing Guide

Complete guide for testing Flow Planner locally and in CI/CD.

## 🧪 Test Suite Overview

Flow Planner uses **pytest** (industry standard) for testing:

- **Unit tests** - Individual component testing
- **Integration tests** - API connectivity and workflow tests
- **Deployment tests** - Verify installation and configuration

---

## 📦 Installation

### Install Test Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development/testing dependencies
pip install -r requirements-dev.txt

# Install Playwright browsers
playwright install chromium
```

---

## 🚀 Running Tests

### Run All Tests

```bash
# Run full test suite
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Run Specific Tests

```bash
# Run deployment verification tests
pytest tests/test_deployment.py

# Run only unit tests
pytest -m unit

# Run only API connectivity tests
pytest -m api

# Run tests matching a pattern
pytest -k "test_import"
```

### Run Legacy Tests

```bash
# Flask setup verification
python test_flask_setup.py

# Browser-Use integration tests
python test_browser_use.py
```

---

## ⚙️ Local Testing Setup

### 1. Environment Variables

Create `.env` file with your API keys:

```bash
# Copy example
cp .env.example .env

# Edit .env and add your keys
GEMINI_API_KEY=your_actual_key_here
ANTHROPIC_API_KEY=your_actual_key_here
SECRET_KEY=your_secret_key_here
```

### 2. Run Tests

```bash
# Quick verification (no API calls)
pytest tests/test_deployment.py::TestImports -v
pytest tests/test_deployment.py::TestConfiguration -v

# With API connectivity (requires valid API keys)
pytest tests/test_deployment.py::TestAPIConnectivity -v

# Full test suite
pytest -v
```

---

## 🔐 GitHub Actions Setup

### Required Secrets

Add these secrets to your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ Yes |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | ✅ Yes |
| `SECRET_KEY` | Flask secret key | ⚠️ Optional (auto-generated for CI) |

### How to Add Secrets

1. **Go to your repository on GitHub**
2. **Click "Settings" → "Secrets and variables" → "Actions"**
3. **Click "New repository secret"**
4. **Add each secret:**

```bash
Name: GEMINI_API_KEY
Value: [paste your Google Gemini API key]

Name: ANTHROPIC_API_KEY
Value: [paste your Anthropic Claude API key]

Name: SECRET_KEY (optional)
Value: [paste a random 64-character hex string]
```

### Generate SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🔄 CI/CD Workflow

### Automated Tests

Tests run automatically on:

- ✅ Push to `main` branch
- ✅ Push to `develop` branch
- ✅ Pull requests to `main`

### What Gets Tested

#### 1. Lint Job
- Black formatting
- isort import sorting
- flake8 linting

#### 2. Security Job
- Bandit security scanning
- Safety dependency vulnerability checks

#### 3. Test Job
- Import verification
- Configuration validation
- File structure checks
- API connectivity tests (if secrets are set)
- Flask app initialization
- Health endpoint checks

---

## 📊 Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=. --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Goals

- **Minimum:** 60% overall coverage
- **Target:** 80% overall coverage
- **Critical modules:** 90%+ coverage

---

## 🧩 Test Categories

### Import Tests (`TestImports`)
Verify all dependencies are installed:
- Flask and extensions
- SocketIO libraries
- AI/ML libraries (Anthropic, Gemini)
- Browser automation (Playwright, Browser-Use)
- Utility libraries

### Configuration Tests (`TestConfiguration`)
Verify environment setup:
- Config module loads
- API keys are set
- Directories exist
- Required files present

### API Connectivity Tests (`TestAPIConnectivity`)
Test external API connections:
- ⚠️ **Requires valid API keys**
- Gemini API ping test
- Claude API ping test
- Playwright browser availability

### Flask Tests (`TestFlaskApplication`)
Test Flask app setup:
- App imports successfully
- Routes are registered
- Configuration is valid
- Health endpoint responds

### Agent Tests (`TestAgentModules`)
Test agent modules import:
- Planner module
- Browser-Use agent
- State capturer
- Refinement agent

---

## 🐛 Troubleshooting

### Issue: API Tests Failing

**Cause:** Invalid or missing API keys

**Solution:**
```bash
# Verify keys are set
python -c "from config import Config; print('Gemini:', bool(Config.GEMINI_API_KEY)); print('Claude:', bool(Config.ANTHROPIC_API_KEY))"

# Test API connectivity manually
pytest tests/test_deployment.py::TestAPIConnectivity::test_gemini_api_connection -v
```

### Issue: Import Errors

**Cause:** Missing dependencies

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Verify imports
pytest tests/test_deployment.py::TestImports -v
```

### Issue: Playwright Browser Not Found

**Cause:** Browsers not installed

**Solution:**
```bash
# Install browsers
playwright install chromium

# With system dependencies (Linux)
playwright install chromium --with-deps
```

### Issue: GitHub Actions Tests Failing

**Cause:** Secrets not configured

**Solution:**
1. Add secrets to repository (see "GitHub Actions Setup" above)
2. Verify secrets in workflow run logs
3. Check `code-quality.yml` workflow file

---

## 📝 Writing New Tests

### Test File Structure

```python
# tests/test_new_feature.py
import pytest
from pathlib import Path

class TestNewFeature:
    """Test new feature functionality"""

    def test_basic_functionality(self):
        """Test basic feature works"""
        # Arrange
        input_data = "test"

        # Act
        result = process_data(input_data)

        # Assert
        assert result == expected_output

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async feature"""
        result = await async_function()
        assert result is not None

    @pytest.mark.slow
    def test_slow_operation(self):
        """Test that takes a long time"""
        # Mark as slow so it can be skipped
        pass
```

### Test Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.api           # API test (requires connectivity)
@pytest.mark.slow          # Slow test (>5 seconds)
@pytest.mark.asyncio       # Async test
```

### Running Marked Tests

```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run only API tests
pytest -m api
```

---

## 🎯 Best Practices

### 1. Test Isolation
- Each test should be independent
- Don't rely on test execution order
- Clean up resources after tests

### 2. Use Fixtures
```python
@pytest.fixture
def temp_directory():
    """Create temporary directory for tests"""
    import tempfile
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
```

### 3. Mock External Dependencies
```python
@pytest.fixture
def mock_api_call(mocker):
    """Mock external API calls"""
    return mocker.patch('module.api_call', return_value='mocked')
```

### 4. Descriptive Test Names
```python
def test_user_registration_with_valid_email_succeeds():
    """✅ Good - describes what's being tested"""
    pass

def test_register():
    """❌ Bad - unclear what's being tested"""
    pass
```

---

## 📚 Additional Resources

- **pytest docs:** https://docs.pytest.org/
- **pytest-asyncio:** https://pytest-asyncio.readthedocs.io/
- **pytest-cov:** https://pytest-cov.readthedocs.io/
- **GitHub Actions:** https://docs.github.com/en/actions

---

## ✅ Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests passing locally
- [ ] Code coverage > 60%
- [ ] GitHub Actions tests passing
- [ ] API keys configured in Railway/deployment platform
- [ ] Environment variables validated
- [ ] Flask app health check responds
- [ ] No security vulnerabilities (Bandit, Safety)
- [ ] Code formatted (Black, isort)
- [ ] No linting errors (flake8)

---

## 🚀 Quick Test Commands

```bash
# Full suite
pytest -v

# Skip slow tests
pytest -m "not slow" -v

# Only imports and config
pytest tests/test_deployment.py::TestImports tests/test_deployment.py::TestConfiguration -v

# With coverage
pytest --cov=. --cov-report=term-missing

# Specific test
pytest tests/test_deployment.py::TestAPIConnectivity::test_gemini_api_connection -v

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l
```

---

**Happy Testing! 🧪**
