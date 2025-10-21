# 🚀 Quick Start Guide

Get up and running in 5 minutes!

---

## 📋 Prerequisites

- Python 3.12+
- Node.js 20+
- Git (optional)

---

## ⚡ 5-Minute Setup

### 1️⃣ Backend Setup (2 minutes)

```bash
# Navigate to project
cd C:\Users\PremArora\Apps\Speech

# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Configure API keys in .env file
# Edit .env and add your keys:
# - SARVAM_API_KEY=your_key
# - OPENAI_API_KEY=your_key
# - ENCRYPTION_KEY=your_generated_key

# Generate encryption key
python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# Run backend
uvicorn backend.main:app --reload
```

✅ Backend running at http://localhost:8000

---

### 2️⃣ Frontend Setup (1 minute)

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Run frontend
npm run dev
```

✅ Frontend running at http://localhost:5173

---

## 🔑 Get Your API Keys

### Required:
1. **Sarvam AI:** https://www.sarvam.ai/ → Sign up → Get API Key
2. **OpenAI:** https://platform.openai.com/api-keys → Create Key

### Add to `.env`:
```bash
SARVAM_API_KEY=your_actual_key_here
OPENAI_API_KEY=your_actual_key_here
ENCRYPTION_KEY=generated_key_from_python_command
```

---

## ✅ Verify Setup

- [ ] Backend: http://localhost:8000/api/v1/health returns `{"status": "healthy"}`
- [ ] API Docs: http://localhost:8000/docs loads
- [ ] Frontend: http://localhost:5173 shows UI
- [ ] Voice chat button visible

---

## 🎯 Test It!

1. Open http://localhost:5173
2. Select optimization level
3. Choose language (Hindi/English)
4. Click "Start Recording"
5. Speak!

---

## 📁 File Structure

```
Speech/
├── .env                    # ⚙️ Backend config (ADD YOUR KEYS HERE)
├── backend/               # 🐍 Python backend
├── frontend/
│   ├── .env              # ⚙️ Frontend config (already set)
│   └── src/              # ⚛️ React components
```

---

## 🆘 Quick Fixes

**Backend won't start?**
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Frontend won't start?**
```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API key errors?**
```bash
# Verify .env file exists and has keys
cat .env | grep API_KEY
```

---

## 📚 More Help

- **Full Setup:** See `SETUP_GUIDE.md`
- **API Docs:** See `backend/API_DOCUMENTATION.md`
- **Components:** See `PHASES_1-4_COMPLETION_SUMMARY.md`

---

## 🎉 You're Done!

**Your Speech AI platform is ready!**

- 🎤 Voice recording
- 🧠 AI responses
- 🌍 22 Indian languages
- 📊 Real-time analytics
- ⚡ Performance controls
