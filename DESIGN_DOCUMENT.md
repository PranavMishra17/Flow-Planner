# AI Workflow Capture System - Design Document

## Executive Summary

An AI-powered web application that automatically captures step-by-step UI workflows with screenshots for any web application task. Users input a natural language request (e.g., "Create a project in Linear"), and the system autonomously navigates the target application, captures screenshots at each step, validates the workflow, and returns a complete visual guide.

**Key Innovation**: Combines web research, AI planning, browser automation, and computer vision to create dynamic workflow documentation without pre-programmed knowledge of specific applications.

---

## 1. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser (User)                        │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Input Form    │  │ Live Progress│  │ Results Gallery │  │
│  │ - Task        │  │ - WebSocket  │  │ - Screenshots   │  │
│  │ - App URL     │  │ - Real-time  │  │ - Step Details  │  │
│  └───────────────┘  └──────────────┘  └─────────────────┘  │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP / WebSocket
               │
┌──────────────▼──────────────────────────────────────────────┐
│                Flask Application Server                      │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ REST API       │  │ WebSocket   │  │ Background Jobs │  │
│  │ - /capture     │  │ - Progress  │  │ - Task Queue    │  │
│  │ - /status      │  │ - Events    │  │ - Workers       │  │
│  │ - /guides      │  └─────────────┘  └─────────────────┘  │
│  └────────────────┘                                         │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│                    Agent Pipeline                            │
│  ┌────────────┐   ┌────────────┐   ┌──────────────────┐    │
│  │  Phase 1   │   │  Phase 2   │   │    Phase 3       │    │
│  │  Planning  │ → │ Execution  │ → │  Validation      │    │
│  │  (Gemini)  │   │(Playwright)│   │(Claude Vision)   │    │
│  └────────────┘   └────────────┘   └──────────────────┘    │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│                  Data & Storage Layer                        │
│  ┌────────────┐   ┌────────────┐   ┌──────────────────┐    │
│  │  SQLite    │   │Screenshots │   │  Generated       │    │
│  │  Database  │   │  /static/  │   │  Guides (JSON)   │    │
│  └────────────┘   └────────────┘   └──────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | HTML + Vanilla JS + Tailwind CSS | Simple, responsive UI |
| **Backend** | Flask (Python 3.10+) | Web server & API |
| **Real-time** | Flask-SocketIO | Live progress updates |
| **Task Queue** | Threading (built-in) | Background job processing |
| **Browser Automation** | Playwright | Web navigation & screenshots |
| **AI Planning** | Google Gemini 1.5 Flash (with Grounding) | Web research + workflow planning |
| **AI Validation** | Anthropic Claude 3.5 Sonnet | Screenshot validation |
| **Database** | SQLite | Workflow metadata storage |
| **Storage** | File System | Screenshots & guides |

---

## 2. Component Breakdown

### 2.1 Frontend (Web UI)

**Purpose**: User interface for submitting tasks and viewing results

**Pages**:

1. **Home Page** (`/`)
   - Task input form
   - App selector/URL input
   - Submit button
   - Recent workflows list

2. **Capture Page** (`/capture/<job_id>`)
   - Live status feed (WebSocket powered)
   - Progress indicator
   - Real-time step updates
   - Screenshot preview as they're captured

3. **Results Page** (`/guide/<guide_id>`)
   - Complete workflow guide
   - Screenshot gallery
   - Step-by-step instructions
   - Download options (JSON, PDF)

**Features**:
- Responsive design (mobile-friendly)
- Real-time WebSocket updates
- Loading states and animations
- Error handling and user feedback

---

### 2.2 Backend (Flask Application)

**Purpose**: API server, request handling, and orchestration

**Main Components**:

#### A. API Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Home page |
| `/api/capture` | POST | Submit new workflow capture job |
| `/api/status/<job_id>` | GET | Get job status |
| `/api/guides` | GET | List all captured workflows |
| `/api/guide/<guide_id>` | GET | Get specific guide details |
| `/static/screenshots/<file>` | GET | Serve screenshot images |

#### B. WebSocket Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `connect` | Client → Server | Client connects |
| `job_update` | Server → Client | Send progress updates |
| `phase_change` | Server → Client | Notify phase transitions |
| `step_captured` | Server → Client | New screenshot available |
| `job_complete` | Server → Client | Workflow capture finished |
| `job_error` | Server → Client | Error occurred |

#### C. Background Job System

**Purpose**: Run workflow capture asynchronously without blocking the web server

**Approach**: Use Python threading with a simple job queue

**Job Lifecycle**:
```
Submitted → Queued → Planning → Executing → Validating → Complete/Failed
```

**Job States**:
- `pending`: Waiting to start
- `planning`: Gemini creating execution plan
- `executing`: Playwright running workflow
- `validating`: Claude checking screenshots
- `completed`: Successfully finished
- `failed`: Error occurred

---

### 2.3 Agent Components

#### A. Gemini Planner

**Purpose**: Research task and create execution plan

**Process**:
1. Receive task description and app URL
2. Use Google Search grounding to find tutorials/documentation
3. Analyze common UI patterns from search results
4. Generate structured execution plan (JSON)
5. Include alternative selectors for robustness

**Output Format**:
```
{
  "research_summary": "Brief summary of findings",
  "steps": [
    {
      "step_number": 1,
      "action": "goto|click|fill|select|wait",
      "description": "Human-readable description",
      "selector": "CSS selector or text",
      "alternative_selectors": ["backup1", "backup2"],
      "value": "For fill/select actions",
      "expected_outcome": "What should happen"
    }
  ]
}
```

**Configuration**:
- Model: `gemini-1.5-flash`
- Tools: `google_search_retrieval`
- Temperature: 0.3 (more deterministic)

---

#### B. Playwright Executor

**Purpose**: Execute planned workflow and capture screenshots

**Capabilities**:
- Launch headless/headed browser
- Navigate to URLs
- Find and interact with UI elements
- Wait for network idle and animations
- Capture full-page or viewport screenshots
- Handle timeouts and errors gracefully

**Execution Actions**:
- `goto`: Navigate to URL
- `click`: Click on element
- `fill`: Type into input field
- `select`: Choose from dropdown
- `wait`: Wait for element or timeout
- `press_key`: Press keyboard keys
- `scroll`: Scroll page

**Error Handling**:
- Retry with alternative selectors
- Capture error state screenshots
- Continue to next step if possible
- Log detailed error information

**Configuration**:
- Browser: Chromium
- Viewport: 1920x1080
- Headless: Configurable (False for development)
- Timeout: 10 seconds per action

---

#### C. Claude Vision Validator

**Purpose**: Validate that each step completed successfully

**Process**:
1. Receive screenshot and step description
2. Analyze screenshot using Claude's vision capabilities
3. Determine if expected outcome occurred
4. Provide validation reason

**Validation Criteria**:
- Expected UI element is visible
- No error messages displayed
- Page is in expected state
- Action had intended effect

**Output**:
```
{
  "is_valid": true/false,
  "reason": "Brief explanation",
  "confidence": "high|medium|low"
}
```

**Configuration**:
- Model: `claude-3-5-sonnet-20241022`
- Max tokens: 1024
- Image format: PNG (base64 encoded)

---

### 2.4 Data Layer

#### A. Database Schema (SQLite)

**Table: workflows**
```
- id (TEXT, PRIMARY KEY)
- task (TEXT)
- app_name (TEXT)
- app_url (TEXT)
- status (TEXT)
- created_at (DATETIME)
- completed_at (DATETIME)
- total_steps (INTEGER)
- successful_steps (INTEGER)
- research_summary (TEXT)
- error_message (TEXT)
```

**Table: steps**
```
- id (TEXT, PRIMARY KEY)
- workflow_id (TEXT, FOREIGN KEY)
- step_number (INTEGER)
- description (TEXT)
- action (TEXT)
- screenshot_path (TEXT)
- url (TEXT)
- validated (BOOLEAN)
- validation_reason (TEXT)
- success (BOOLEAN)
- error_message (TEXT)
```

#### B. File Storage

**Directory Structure**:
```
/app
  /static
    /screenshots
      /{workflow_id}
        /step_1.png
        /step_2.png
        ...
  /guides
    /{workflow_id}.json
```

**Screenshot Naming**: `{workflow_id}_step_{number}.png`

**Guide Format**: JSON file with complete workflow data

---

## 3. Environment Configuration

### Required API Keys

**`.env` File Structure**:
```
# Google Gemini API (Required)
GEMINI_API_KEY=AIzaSy...

# Anthropic Claude API (Required for validation)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Flask Configuration
FLASK_SECRET_KEY=your-random-secret-key
FLASK_ENV=development

# Application Settings
ENABLE_VALIDATION=true
HEADLESS_BROWSER=false
MAX_CONCURRENT_JOBS=3
```

### API Key Acquisition

1. **Gemini API Key** (Free)
   - URL: https://aistudio.google.com/app/apikey
   - Free tier: 60 requests/minute
   - Cost: $0 for Flash model

2. **Anthropic API Key** ($5 free credit)
   - URL: https://console.anthropic.com/
   - Free credit: $5 (enough for ~1,600 screenshots)
   - Cost after: ~$3 per 1,000 images

### Configuration Options

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENABLE_VALIDATION` | `true` | Enable Claude vision validation |
| `HEADLESS_BROWSER` | `false` | Run browser in background |
| `MAX_CONCURRENT_JOBS` | `3` | Concurrent capture jobs |
| `SCREENSHOT_QUALITY` | `80` | PNG compression quality |
| `MAX_STEPS` | `15` | Maximum steps per workflow |

---

## 4. Data Flow

### Workflow Capture Sequence

```
1. User Input
   ├─→ Task: "Create a project in Linear"
   ├─→ App URL: https://linear.app
   └─→ App Name: Linear

2. Job Creation
   ├─→ Generate unique job_id
   ├─→ Save to database (status: pending)
   ├─→ Add to job queue
   └─→ Return job_id to frontend

3. WebSocket Connection
   ├─→ Frontend connects to job_id room
   └─→ Backend ready to send updates

4. Phase 1: Planning (Gemini)
   ├─→ Emit: "phase_change: planning"
   ├─→ Gemini searches web for tutorials
   ├─→ Gemini generates execution plan
   ├─→ Save plan to database
   └─→ Emit: "plan_created" with step count

5. Phase 2: Execution (Playwright)
   ├─→ Emit: "phase_change: executing"
   ├─→ Launch browser
   └─→ For each step:
       ├─→ Execute action
       ├─→ Wait for UI to settle
       ├─→ Capture screenshot
       ├─→ Save screenshot to disk
       ├─→ Emit: "step_captured" with preview
       └─→ Save step to database

6. Phase 3: Validation (Claude)
   ├─→ Emit: "phase_change: validating"
   └─→ For each step:
       ├─→ Send screenshot to Claude
       ├─→ Receive validation result
       ├─→ Update step in database
       └─→ Emit: "step_validated"

7. Completion
   ├─→ Generate final guide (JSON)
   ├─→ Update workflow status: completed
   ├─→ Emit: "job_complete" with guide URL
   └─→ Close browser

8. Error Handling
   ├─→ Catch any errors at any phase
   ├─→ Log error details
   ├─→ Update workflow status: failed
   ├─→ Emit: "job_error" with message
   └─→ Cleanup resources
```

---

## 5. Implementation Approach

### Phase 1: Core Foundation (Days 1-2)

**Goal**: Basic workflow capture without UI

**Tasks**:
1. Set up Flask application structure
2. Implement Gemini Planner component
3. Implement Playwright Executor component
4. Test with one hardcoded workflow
5. Verify screenshots are captured correctly

**Success Criteria**:
- Can run script and get screenshots for Linear project creation

---

### Phase 2: Validation & Reliability (Days 2-3)

**Goal**: Add Claude validation and error handling

**Tasks**:
1. Implement Claude Vision Validator
2. Add error handling and retries
3. Add alternative selector fallbacks
4. Test with 2-3 different workflows
5. Refine selector strategies

**Success Criteria**:
- Validation accurately detects success/failure
- System handles common errors gracefully

---

### Phase 3: Flask Backend (Days 3-4)

**Goal**: API server with job queue

**Tasks**:
1. Create Flask app structure
2. Implement REST API endpoints
3. Add SQLite database integration
4. Implement background job queue
5. Add file storage for screenshots/guides

**Success Criteria**:
- Can submit jobs via API
- Jobs run in background
- Can retrieve results via API

---

### Phase 4: Real-time Updates (Days 4-5)

**Goal**: WebSocket for live progress

**Tasks**:
1. Add Flask-SocketIO integration
2. Implement progress event emitters
3. Test real-time update flow
4. Add connection handling
5. Handle disconnects gracefully

**Success Criteria**:
- Frontend receives real-time updates
- Progress visible during execution

---

### Phase 5: Frontend UI (Days 5-6)

**Goal**: User-friendly web interface

**Tasks**:
1. Create HTML templates
2. Implement task submission form
3. Build live progress display
4. Create results viewer
5. Add styling with Tailwind CSS

**Success Criteria**:
- Users can submit tasks via web form
- See live progress
- View completed guides

---

### Phase 6: Polish & Testing (Day 7)

**Goal**: Production-ready system

**Tasks**:
1. Test with 5+ different workflows
2. Add comprehensive error messages
3. Improve UI/UX
4. Add guide export options
5. Create documentation

**Success Criteria**:
- System handles diverse workflows
- Professional appearance
- Clear documentation

---

## 6. File Structure

```
workflow-capture/
├── .env                          # API keys (not in git)
├── .gitignore
├── requirements.txt              # Python dependencies
├── README.md                     # Setup instructions
├── DESIGN_DOCUMENT.md           # This document
│
├── app.py                        # Flask application entry point
│
├── agent/
│   ├── __init__.py
│   ├── planner.py               # Gemini planning logic
│   ├── executor.py              # Playwright execution
│   └── validator.py             # Claude vision validation
│
├── models/
│   ├── __init__.py
│   ├── database.py              # SQLite setup & queries
│   └── workflow.py              # Workflow data models
│
├── routes/
│   ├── __init__.py
│   ├── api.py                   # API endpoints
│   └── pages.py                 # Page routes
│
├── jobs/
│   ├── __init__.py
│   ├── queue.py                 # Job queue management
│   └── worker.py                # Background worker
│
├── templates/                    # HTML templates
│   ├── base.html
│   ├── index.html               # Home page
│   ├── capture.html             # Live progress page
│   └── guide.html               # Results page
│
├── static/
│   ├── css/
│   │   └── styles.css           # Custom styles
│   ├── js/
│   │   ├── capture.js           # WebSocket client
│   │   └── main.js              # General JS
│   └── screenshots/             # Generated screenshots
│       └── {workflow_id}/
│
├── guides/                       # Generated JSON guides
│   └── {workflow_id}.json
│
└── workflows.db                 # SQLite database
```

---

## 7. Key Design Decisions

### Why Flask over FastAPI?
- Simpler for small-to-medium applications
- Excellent Flask-SocketIO integration
- Large ecosystem and community
- Easier deployment options

### Why Threading over Celery?
- Simpler setup (no Redis/RabbitMQ needed)
- Sufficient for expected load (few concurrent jobs)
- Easier to debug and develop
- Can migrate to Celery later if needed

### Why SQLite over PostgreSQL?
- Zero configuration required
- File-based (easy backup and portability)
- Sufficient for expected data volume
- Can migrate to PostgreSQL in production if needed

### Why Vanilla JS over React?
- Simpler, faster development
- No build process needed
- Smaller bundle size
- Sufficient for this application's complexity

### Why Gemini over GPT-4?
- Native web search grounding (no separate API)
- Free tier with generous limits
- Fast inference (Flash model)
- Good quality for planning tasks

---

## 8. Cost Analysis

### Per Workflow Cost Estimate

| Component | Cost | Notes |
|-----------|------|-------|
| Gemini Flash | $0.00 | Free tier: 60 req/min |
| Playwright | $0.00 | Open source |
| Claude Vision (6 steps) | $0.018 | ~$3 per 1,000 images |
| **Total per workflow** | **~$0.02** | Very low cost |

### Monthly Estimates

**100 workflows/month**: ~$2.00
**1,000 workflows/month**: ~$20.00

**Free tier limits**:
- Gemini: Essentially unlimited for this use case
- Claude: $5 free credit = ~250 workflows

---

## 9. Testing Strategy

### Test Cases

**Must test 3-5 workflows across 1-2 apps**:

**Linear Workflows**:
1. Create a new project
2. Create an issue
3. Filter issues by status
4. Change project settings

**Notion Workflows** (if time permits):
1. Create a new page
2. Add a database
3. Filter database view

### Testing Approach

1. **Manual Testing**: Run each workflow and verify
2. **Visual Inspection**: Check screenshots for quality
3. **Validation Testing**: Ensure Claude correctly validates
4. **Error Testing**: Test with invalid URLs, wrong selectors
5. **Edge Cases**: Test with slow-loading pages, dynamic content

---

## 10. Deployment Considerations

### Development
- Run locally with `flask run`
- Browser in non-headless mode for debugging
- Hot reload enabled
- Detailed logging

### Production (Future)
- Use Gunicorn or uWSGI
- Run browser in headless mode
- Use nginx as reverse proxy
- Consider cloud storage for screenshots (S3)
- Add authentication/rate limiting
- Use PostgreSQL instead of SQLite
- Implement proper job queue (Celery + Redis)

---

## 11. Success Metrics

### Functional Success
- ✅ Can capture 5 different workflows
- ✅ Screenshots are clear and relevant
- ✅ Validation accuracy >80%
- ✅ Handles errors gracefully
- ✅ Live progress updates work reliably

### Quality Metrics
- Average workflow capture time: <2 minutes
- Screenshot quality: Clear and readable
- Validation accuracy: >80% correct
- System uptime: No crashes during testing
- User experience: Intuitive and responsive

---

## 12. Future Enhancements

### Phase 2 Features (Post-MVP)
- **Multi-browser support**: Firefox, Safari
- **Video recording**: Capture full video of workflow
- **Export formats**: PDF, Markdown, HTML
- **Workflow templates**: Save and reuse plans
- **Collaboration**: Share guides with teams
- **API access**: Let other apps use the system
- **Scheduled captures**: Auto-update guides periodically
- **A/B testing**: Capture variations of workflows

### Advanced Features
- **Interactive playback**: Step through workflow in browser
- **Diff detection**: Compare workflow changes over time
- **Multi-language support**: Internationalization
- **Custom branding**: White-label for enterprises
- **Analytics**: Track workflow usage and success rates

---

## 13. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | Medium | Implement caching, use free tiers wisely |
| Selector failures | High | Multiple fallback selectors, smart retry logic |
| Dynamic content | Medium | Generous wait times, network idle detection |
| Browser crashes | Medium | Error handling, automatic restart |
| Cost overruns | Low | Monitor usage, implement hard limits |
| Poor validation | Medium | Tune prompts, add confidence scores |

---

## 14. Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Foundation | 2 days | Working agent pipeline |
| Validation | 1 day | Reliable capture with validation |
| Backend | 1 day | Flask API with job queue |
| Real-time | 1 day | WebSocket progress updates |
| Frontend | 1 day | Complete UI |
| Testing | 1 day | 5 tested workflows |
| **Total** | **7 days** | **Production-ready MVP** |

---

## 15. Conclusion

This design provides a clear path to building a functional, AI-powered workflow capture system. The architecture is deliberately simple to enable rapid development while remaining extensible for future enhancements.

**Key Strengths**:
- Clear separation of concerns
- Modular components
- Real-time user feedback
- Low operational cost
- Simple deployment

**Next Steps**:
1. Set up development environment
2. Acquire API keys
3. Begin Phase 1 implementation
4. Test iteratively with real workflows

The system is designed to be built incrementally, with each phase adding value while maintaining a working product at each stage.
