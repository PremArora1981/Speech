# Setup Guide - Speech AI Platform

This guide will help you set up the Speech AI platform for local development.

---

## 📋 Prerequisites

- **Python 3.12+** installed
- **Node.js 20+** and npm installed
- **Git** installed (optional, for version control)

---

## 🚀 Quick Start (Local Development)

### Step 1: Backend Setup

1. **Navigate to project root:**
   ```bash
   cd C:\Users\PremArora\Apps\Speech
   ```

2. **Create Python virtual environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment:**
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

4. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure environment variables:**

   The `.env` file has been created at the root directory. **You need to add your API keys:**

   ```bash
   # Edit .env file and add:
   SARVAM_API_KEY=your_actual_sarvam_key
   OPENAI_API_KEY=your_actual_openai_key
   ENCRYPTION_KEY=your_generated_encryption_key
   ```

   **To generate an encryption key:**
   ```bash
   python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
   ```
   Copy the output and paste it as `ENCRYPTION_KEY` in `.env`

7. **Initialize the database:**
   ```bash
   # Run migrations (if using Alembic)
   alembic upgrade head

   # Or let the app create SQLite database on first run
   ```

8. **Run the backend:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Backend will be available at: http://localhost:8000

   **Test it:**
   - Health check: http://localhost:8000/api/v1/health
   - API docs: http://localhost:8000/docs
   - Metrics: http://localhost:8000/metrics

---

### Step 2: Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**

   The `frontend/.env` file has been created. It's already configured for local development:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000
   VITE_WS_BASE_URL=ws://localhost:8000
   VITE_API_KEY=dev_api_key_12345
   ```

4. **Run the frontend:**
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:5173

---

## 🔑 Getting API Keys

### Sarvam AI (Required)
1. Go to https://www.sarvam.ai/
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into `.env` as `SARVAM_API_KEY`

### OpenAI (Required for RAG)
1. Go to https://platform.openai.com/
2. Sign up for an account
3. Navigate to https://platform.openai.com/api-keys
4. Create a new API key
5. Copy and paste into `.env` as `OPENAI_API_KEY`

### ElevenLabs (Optional)
1. Go to https://elevenlabs.io/
2. Sign up for an account
3. Navigate to Profile Settings → API Keys
4. Copy your API key
5. Add to `.env` as `ELEVENLABS_API_KEY`

---

## 📁 Environment Files Location

```
Speech/
├── .env                    # Backend configuration (ROOT LEVEL)
├── .env.example           # Backend template
├── frontend/
│   ├── .env               # Frontend configuration
│   └── .env.example       # Frontend template
```

**Important:**
- `.env` files contain sensitive information (API keys)
- They are already in `.gitignore` and won't be committed
- `.env.example` files are templates without actual keys (safe to commit)

---

## 🔧 Configuration Details

### Backend `.env` (Root Directory)

**Required Variables:**
```bash
# Minimum required for basic functionality
SARVAM_API_KEY=your_key              # For ASR, LLM, TTS
OPENAI_API_KEY=your_key              # For RAG embeddings
ENCRYPTION_KEY=your_generated_key    # For encrypting secrets
DATABASE_URL=sqlite:///./speech.db   # Default SQLite
```

**Optional Variables:**
```bash
# Redis caching (improves performance)
REDIS_URL=redis://localhost:6379/0

# ElevenLabs (if using their voices)
ELEVENLABS_API_KEY=your_key

# Weaviate (if using external instance)
WEAVIATE_URL=http://localhost:8080

# LiveKit (for telephony features)
LIVEKIT_PROJECT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
```

### Frontend `.env` (frontend/ Directory)

**Required Variables:**
```bash
# Already configured for local dev
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_API_KEY=dev_api_key_12345
```

---

## 🐳 Docker Setup (Alternative)

If you prefer Docker:

1. **Ensure `.env` is configured** (same as above)

2. **Build and start all services:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f backend
   ```

4. **Stop services:**
   ```bash
   docker-compose down
   ```

**Services started:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Weaviate: localhost:8080

**With monitoring (optional):**
```bash
docker-compose --profile monitoring up -d
```
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

---

## ✅ Verification Checklist

### Backend Verification
- [ ] Virtual environment activated (`.venv`)
- [ ] Dependencies installed successfully
- [ ] `.env` file exists with API keys
- [ ] Backend starts without errors: `uvicorn backend.main:app --reload`
- [ ] Health check works: http://localhost:8000/api/v1/health
- [ ] API docs accessible: http://localhost:8000/docs

### Frontend Verification
- [ ] Node modules installed (`npm install`)
- [ ] Frontend `.env` exists
- [ ] Frontend starts without errors: `npm run dev`
- [ ] Frontend accessible: http://localhost:5173
- [ ] Can see UI components

---

## 🔍 Troubleshooting

### Backend Issues

**ImportError: No module named 'backend'**
```bash
# Make sure you're in the project root directory
cd C:\Users\PremArora\Apps\Speech

# And virtual environment is activated
.venv\Scripts\activate
```

**Database errors**
```bash
# Initialize database
alembic upgrade head

# Or delete and recreate
rm speech.db
# Restart backend to auto-create
```

**API key errors**
```bash
# Verify .env file exists
ls .env

# Check API keys are set (no spaces, no quotes)
SARVAM_API_KEY=abc123xyz  # ✅ Correct
SARVAM_API_KEY="abc123"   # ❌ Remove quotes
SARVAM_API_KEY = abc123   # ❌ Remove spaces
```

### Frontend Issues

**Module not found errors**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**CORS errors**
```bash
# Verify backend is running first
# Check frontend .env has correct API URL
VITE_API_BASE_URL=http://localhost:8000
```

**WebSocket connection failed**
```bash
# Ensure backend is running
# Verify WebSocket URL
VITE_WS_BASE_URL=ws://localhost:8000  # Not wss:// for local dev
```

---

## 📚 Next Steps

1. **Test the voice chat:**
   - Open http://localhost:5173
   - Click "Start Recording"
   - Speak in Hindi or English
   - Verify response

2. **Explore components:**
   - Try PerformanceSettings (quality-latency tradeoff)
   - Configure BargeInSettings (interruption behavior)
   - Browse VoiceSettings (voice selection)

3. **View analytics:**
   - Check CostTracker
   - Review SessionMetrics
   - See LatencyIndicator

4. **Monitor system:**
   - Prometheus metrics: http://localhost:8000/metrics
   - Logs in terminal

---

## 🆘 Getting Help

**Documentation:**
- API Documentation: `backend/API_DOCUMENTATION.md`
- Frontend README: `frontend/README.md`
- Architecture: `docs/architecture.md`
- Phases 1-4 Summary: `PHASES_1-4_COMPLETION_SUMMARY.md`

**Common Files:**
- Backend config: `backend/config/settings.py`
- Environment template: `.env.example`
- Docker setup: `docker-compose.yml`

**Need more help?**
- Check error messages carefully
- Review logs in terminal
- Verify all API keys are valid
- Ensure all services are running

---

## 🎉 You're Ready!

Once both backend and frontend are running without errors, you have a fully functional Speech AI platform ready for development and testing!

**Default Access:**
- Frontend UI: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Metrics: http://localhost:8000/metrics
