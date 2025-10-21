# Speech AI Platform - Startup Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- Redis (optional, for caching)
- PostgreSQL (optional, defaults to SQLite)

## Backend Setup & Run

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root (optional, has sensible defaults):

```env
# Core Settings
ENVIRONMENT=development
DEBUG=false
API_KEY=dev_api_key_12345

# API Keys (required)
SARVAM_API_KEY=your_sarvam_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional
ELEVENLABS_API_KEY=your_elevenlabs_key_here  # Optional

# Database (defaults to SQLite)
DATABASE_URL=sqlite:///./speech.db

# Redis Cache (optional)
REDIS_URL=redis://localhost:6379/0

# Weaviate Vector DB (for RAG)
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=  # Optional

# LiveKit (for telephony, optional)
LIVEKIT_PROJECT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

### 3. Initialize Database

```bash
python -c "from backend.database.models import Base; from backend.database import engine; Base.metadata.create_all(bind=engine)"
```

### 4. Start Backend Server

```bash
# Development (with hot reload)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The backend API will be available at:
- **REST API**: http://localhost:8000/api/v1
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Metrics**: http://localhost:8000/metrics
- **WebSocket**: ws://localhost:8000/api/v1/voice-session

## Frontend Setup & Run

### 1. Install Node Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

The frontend uses sensible defaults, but you can override them by creating `frontend/.env`:

```env
VITE_API_KEY=dev_api_key_12345
VITE_API_URL=http://localhost:8000/api/v1
VITE_VOICE_WS_URL=ws://localhost:8000/api/v1/voice-session
VITE_TTS_URL=http://localhost:8000/api/v1/tts
```

### 3. Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at:
- **Development**: http://localhost:5173

### 4. Build for Production

```bash
cd frontend
npm run build
```

The production build will be in `frontend/dist/`.

## Using Docker Compose (Recommended for Full Stack)

### 1. Create `.env` File

Create a `.env` file in the project root with your API keys:

```env
SARVAM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
ENCRYPTION_KEY=your_base64_encryption_key
LIVEKIT_PROJECT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

### 2. Start All Services

```bash
# Start core services (backend, frontend, databases)
docker compose up

# Include monitoring (Prometheus, Grafana)
docker compose --profile monitoring up
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Prometheus**: http://localhost:9090 (with monitoring profile)
- **Grafana**: http://localhost:3001 (with monitoring profile)

### 3. Stop Services

```bash
docker compose down
```

## Troubleshooting

### Backend Issues

**Import Error: No module named 'prometheus_client'**
```bash
pip install -r requirements.txt
```

**WebSocket Connection Failed**
- Ensure backend is running on port 8000
- Check that `API_KEY` matches between frontend and backend
- Verify no firewall is blocking WebSocket connections
- The backend now properly handles WebSocket upgrade requests

**Database Error**
```bash
# Recreate database tables
python -c "from backend.database.models import Base; from backend.database import engine; Base.metadata.create_all(bind=engine)"
```

### Frontend Issues

**Failed to fetch / Connection Refused**
- Ensure backend is running on http://localhost:8000
- Check CORS settings in `backend/main.py`
- Verify API_KEY is set correctly

**WebSocket Errors**
- Verify `VITE_VOICE_WS_URL` points to `ws://localhost:8000/api/v1/voice-session`
- Ensure `VITE_API_KEY` matches the backend's `API_KEY`

### Redis Connection Issues

If you don't need caching, you can run without Redis by not setting `REDIS_URL`.

## Testing

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest backend/tests/test_tts_service.py

# Run with coverage
pytest --cov=backend
```

### Frontend Tests

```bash
cd frontend
npm test
```

## API Authentication

All API endpoints (except `/health`) require authentication via:
- **Header**: `X-API-Key: your_api_key`
- **Query Parameter** (WebSocket only): `?api_key=your_api_key`

Default API key for development: `dev_api_key_12345`

## Next Steps

1. Set up your API keys in `.env`
2. Start backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
3. Start frontend: `cd frontend && npm run dev`
4. Open http://localhost:5173 in your browser
5. Test the voice chat interface

For production deployment, use Docker Compose or deploy services separately with proper environment configuration.




