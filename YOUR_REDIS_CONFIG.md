# Your Redis Configuration

## 📋 Your Redis Details

**Provider:** Redis Cloud
**Endpoint:** `redis-11680.crce217.ap-south-1-1.ec2.redns.redis-cloud.com:11680`
**Database:** `database-MGRTHXEX`
**Port:** `11680`
**Region:** `ap-south-1` (AWS Mumbai)

---

## 🔑 Getting Your Password

### Step 1: Access Redis Cloud Dashboard
Go to: https://app.redislabs.com/

### Step 2: Find Your Database
Click on: **database-MGRTHXEX**

### Step 3: Get Password
Look for one of these sections:
- **"Security"** tab → Default user password
- **"Configuration"** → Security → Default user password
- **"General"** section → Password field

### Step 4: Copy Password
Click "Show" or "Copy" button next to the password field

---

## ⚙️ Configuration Steps

### 1. Edit `.env` File

Open: `C:\Users\PremArora\Apps\Speech\.env`

### 2. Find the Redis Section

Look for line 26:
```bash
REDIS_URL=rediss://default:YOUR_REDIS_PASSWORD_HERE@redis-11680.crce217.ap-south-1-1.ec2.redns.redis-cloud.com:11680/0
```

### 3. Replace Password

Replace `YOUR_REDIS_PASSWORD_HERE` with your actual password:
```bash
# Example (use YOUR actual password):
REDIS_URL=rediss://default:abc123XYZ@redis-11680.crce217.ap-south-1-1.ec2.redns.redis-cloud.com:11680/0
```

### 4. Save File

Save the `.env` file.

---

## ✅ Testing Your Configuration

### Start Backend
```bash
# Navigate to project
cd C:\Users\PremArora\Apps\Speech

# Activate virtual environment
.venv\Scripts\activate

# Start backend
uvicorn backend.main:app --reload
```

### Check Connection

**Look for in logs:**
```
INFO: Connected to Redis at rediss://...
```

**OR if there's an error:**
```
ERROR: Failed to connect to Redis: ...
```

### Test Caching

1. Make an API request (e.g., voice chat)
2. Make the **same request again**
3. Second request should be **much faster** (cached)

### Check Metrics

Visit: http://localhost:8000/metrics

Look for:
```
cache_hits_total{cache_type="llm"} 5
cache_misses_total{cache_type="llm"} 2
```

---

## 🚨 Troubleshooting

### Error: "Authentication required"
**Problem:** Password is incorrect or missing
**Solution:**
- Double-check password from Redis Cloud dashboard
- Ensure no extra spaces before/after password
- Password is case-sensitive

### Error: "Connection refused"
**Problem:** Network/firewall issue
**Solution:**
- Check if your IP is whitelisted in Redis Cloud
- Go to Redis Cloud → database-MGRTHXEX → Security → Source IPs
- Add `0.0.0.0/0` to allow all IPs (for testing)

### Error: "SSL certificate verify failed"
**Problem:** SSL/TLS issue
**Solution:**
- Ensure you're using `rediss://` (double 's')
- Not `redis://` (single 's')

### Error: "Connection timeout"
**Problem:** Network connectivity
**Solution:**
- Check internet connection
- Verify endpoint is correct
- Try from different network

---

## 📊 What Gets Cached

### LLM Responses
- **What:** AI conversation responses
- **Duration:** 10-60 minutes
- **Benefit:** 50-100x faster responses
- **Cost Savings:** 70-90% reduction in API calls

### TTS Audio
- **What:** Synthesized voice audio
- **Duration:** 5-30 minutes
- **Benefit:** Instant audio playback
- **Cost Savings:** 80-95% reduction in TTS costs

### Example Savings
```
Without Cache:
- 100 requests
- 100 API calls to Sarvam/OpenAI
- Cost: $10

With Cache (80% hit rate):
- 100 requests
- 20 API calls (80 from cache)
- Cost: $2
- Savings: $8 (80%)
```

---

## 🔒 Security Notes

### ✅ Good Practices
- **Never commit** `.env` to Git (already in `.gitignore`)
- **Use strong password** from Redis Cloud
- **Enable SSL** with `rediss://` (already configured)
- **Whitelist IPs** in Redis Cloud for production

### ⚠️ Never Do This
- Don't use `redis://` (without SSL) for remote Redis
- Don't share password in chat/email
- Don't commit password to GitHub
- Don't use same password for dev/prod

---

## 📈 Monitoring Cache Performance

### Method 1: Backend Logs
```bash
INFO: LLM cache hit for query: "what is the weather"
INFO: TTS cache hit for voice: meera, text: "नमस्ते"
```

### Method 2: Prometheus Metrics
Visit: http://localhost:8000/metrics
```
cache_hits_total{cache_type="llm",optimization_level="balanced"} 42
cache_misses_total{cache_type="llm",optimization_level="balanced"} 8
cache_size_bytes{cache_type="llm"} 1048576
```

### Method 3: Frontend UI
The **CostTracker** component shows:
- Total requests
- Cache hit rate
- Cost savings from caching

### Method 4: Redis Cloud Dashboard
Go to: https://app.redislabs.com/
- See memory usage
- See operations per second
- See connected clients

---

## 🎯 Your Complete Configuration

```bash
# File: C:\Users\PremArora\Apps\Speech\.env

# REDIS URL (Line 26)
REDIS_URL=rediss://default:YOUR_PASSWORD@redis-11680.crce217.ap-south-1-1.ec2.redns.redis-cloud.com:11680/0

# Breakdown:
# Protocol: rediss (SSL)
# Username: default
# Password: YOUR_PASSWORD (get from dashboard)
# Hostname: redis-11680.crce217.ap-south-1-1.ec2.redns.redis-cloud.com
# Port: 11680
# Database: 0 (default)
```

---

## 📞 Need Help?

### Redis Cloud Support
- Dashboard: https://app.redislabs.com/
- Docs: https://docs.redis.com/latest/rc/
- Support: https://redis.com/company/support/

### Project Documentation
- Full Redis Setup: `REDIS_SETUP.md`
- Quick Start: `QUICKSTART.md`
- Setup Guide: `SETUP_GUIDE.md`

---

## ✨ Summary

1. ✅ Redis Cloud endpoint configured in `.env`
2. ⏳ **Need:** Password from Redis Cloud dashboard
3. 🔄 **Replace:** `YOUR_REDIS_PASSWORD_HERE` in line 26
4. 💾 **Save** `.env` file
5. 🚀 **Restart** backend
6. ✅ **Verify** in logs and metrics

**Once password is added, you're all set!**
