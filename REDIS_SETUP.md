# Redis Setup Guide

This guide explains how to configure Redis for caching in the Speech AI platform.

---

## 📋 What Redis is Used For

Redis provides caching for:
1. **LLM Responses** - Exact match and semantic similarity caching
2. **TTS Audio** - Audio synthesis results
3. **Cost Optimization** - Reduces API calls by serving cached responses

**Cache Benefits:**
- 🚀 **Faster responses** (milliseconds vs seconds)
- 💰 **Lower costs** (fewer API calls to Sarvam/OpenAI/ElevenLabs)
- 📈 **Better scalability** (handles more concurrent users)

---

## 🔧 Redis Configuration Formats

### Format 1: Basic (No Authentication)
```bash
REDIS_URL=redis://hostname:6379/0
```

### Format 2: With Password
```bash
REDIS_URL=redis://:password@hostname:6379/0
```

### Format 3: With Username and Password
```bash
REDIS_URL=redis://username:password@hostname:6379/0
```

### Format 4: With TLS/SSL (Secure)
```bash
REDIS_URL=rediss://username:password@hostname:6379/0
# Note: "rediss" (with double 's') for SSL
```

---

## 🌐 Common Redis Providers

### Option 1: Redis Cloud (Recommended for Production)
**Website:** https://redis.com/try-free/

**Setup Steps:**
1. Sign up for free account
2. Create a new database
3. Get your endpoint and password
4. Format: `rediss://default:password@endpoint:port/0`

**Example:**
```bash
REDIS_URL=rediss://default:abc123xyz@my-redis.redis.cloud:12345/0
```

### Option 2: Upstash (Serverless Redis)
**Website:** https://upstash.com/

**Setup Steps:**
1. Sign up for free account
2. Create a Redis database
3. Copy the connection string from dashboard
4. It will be pre-formatted for you

**Example:**
```bash
REDIS_URL=rediss://default:AbC123XyZ@us1-caring-owl-12345.upstash.io:6379
```

### Option 3: Railway
**Website:** https://railway.app/

**Setup Steps:**
1. Sign up for account
2. Create new project
3. Add Redis service
4. Copy connection URL from Variables tab

**Example:**
```bash
REDIS_URL=redis://default:password@redis.railway.internal:6379
```

### Option 4: Local Redis (Development Only)
**For Windows:**
1. Download Redis from https://github.com/microsoftarchive/redis/releases
2. Install and run Redis server
3. Use: `REDIS_URL=redis://localhost:6379/0`

**For Linux/Mac:**
```bash
# Install
brew install redis  # Mac
sudo apt-get install redis-server  # Ubuntu

# Start
redis-server

# Use
REDIS_URL=redis://localhost:6379/0
```

---

## 🔑 Finding Your Redis Connection Details

### You Need:
1. **Hostname/Endpoint** - e.g., `my-redis.cloud.com`
2. **Port** - Usually `6379` (default) or custom like `12345`
3. **Password** - Your Redis password (if authentication is enabled)
4. **Username** - Usually `default` (can be omitted if using password only)
5. **Database Number** - Usually `/0` (default database)
6. **SSL/TLS** - Use `rediss://` if SSL is enabled, `redis://` if not

### Example Breakdown:
```
rediss://default:mypassword123@my-endpoint.upstash.io:6379/0
│      │       │               │                        │    │
│      │       │               │                        │    └─ Database number
│      │       │               │                        └────── Port
│      │       │               └────────────────────────────── Hostname
│      │       └────────────────────────────────────────────── Password
│      └────────────────────────────────────────────────────── Username
└───────────────────────────────────────────────────────────── Protocol (rediss = SSL)
```

---

## ⚙️ Configuration in `.env`

### Step 1: Get Your Connection String

From your Redis provider dashboard, copy the connection string.

### Step 2: Add to `.env`

Edit `C:\Users\PremArora\Apps\Speech\.env`:

```bash
# ============================================================================
# REDIS (CACHING)
# ============================================================================
# Add your Redis connection string here
REDIS_URL=rediss://default:your_password@your-endpoint.com:6379/0

# Optional: Customize cache TTL (time-to-live in seconds)
TTS_CACHE_TTL_QUALITY=1800    # 30 minutes
TTS_CACHE_TTL_BALANCED=900    # 15 minutes
TTS_CACHE_TTL_SPEED=300       # 5 minutes
```

### Step 3: Restart Backend

```bash
# Stop backend (Ctrl+C)
# Start again
uvicorn backend.main:app --reload
```

---

## 🧪 Testing Redis Connection

### Method 1: Check Backend Logs

When you start the backend, you should see:
```
INFO: Connected to Redis at rediss://...
```

### Method 2: Test Endpoint

1. Make a request to the API
2. Make the same request again
3. Second request should be much faster (cached)

### Method 3: Redis CLI (if available)

```bash
# Connect to Redis
redis-cli -h your-endpoint.com -p 6379 -a your_password

# Test connection
PING
# Should return: PONG

# Check cache keys
KEYS llm:*
KEYS tts:*

# Check database size
DBSIZE
```

---

## 📊 Monitoring Cache Performance

### Backend Logs
The backend logs show cache hit/miss:
```
INFO: LLM cache hit for query: ...
INFO: TTS cache hit for voice: ...
```

### Prometheus Metrics
Visit http://localhost:8000/metrics and look for:
```
cache_hits_total{cache_type="llm",optimization_level="balanced"} 42
cache_misses_total{cache_type="llm",optimization_level="balanced"} 8
```

### Frontend CostTracker Component
The CostTracker component shows:
- Cache hit rate
- Cost savings from caching

---

## 🔒 Security Best Practices

### 1. Always Use SSL in Production
```bash
# Use rediss:// not redis://
REDIS_URL=rediss://...  # ✅ Secure
REDIS_URL=redis://...   # ❌ Not encrypted
```

### 2. Never Commit Redis Credentials
- `.env` is in `.gitignore` ✅
- Never push to GitHub
- Use separate Redis instances for dev/staging/prod

### 3. Use Strong Passwords
```bash
# ❌ Weak
REDIS_URL=rediss://default:password123@...

# ✅ Strong
REDIS_URL=rediss://default:aB9$xK2#mN7@pQ4...
```

### 4. Limit Network Access
- Configure firewall rules
- Use VPC/Private networking in production
- Whitelist only your backend server IP

---

## 🚨 Troubleshooting

### Connection Refused
```
Error: Connection refused
```

**Solutions:**
- Check hostname/endpoint is correct
- Verify port number (usually 6379)
- Check firewall/security group allows connections
- Ensure Redis server is running

### Authentication Failed
```
Error: NOAUTH Authentication required
```

**Solutions:**
- Add password to connection string
- Format: `redis://:password@host:port/0` (note the colon before password)

### SSL/TLS Errors
```
Error: SSL connection failed
```

**Solutions:**
- Use `rediss://` (with double 's') for SSL connections
- Use `redis://` (single 's') for non-SSL
- Check if your Redis provider requires SSL

### Timeout Errors
```
Error: Connection timeout
```

**Solutions:**
- Check network connectivity
- Verify endpoint is accessible
- Try increasing timeout in code
- Check if IP is whitelisted

---

## 💡 Tips & Best Practices

### 1. Development Without Redis
If you don't have Redis, **caching is automatically disabled**:
```bash
# Comment out or leave empty
# REDIS_URL=
```
The app will work fine, just without caching benefits.

### 2. Cache TTL Guidelines
```bash
# Quality level (expensive, cache longer)
TTS_CACHE_TTL_QUALITY=3600    # 1 hour

# Balanced (moderate)
TTS_CACHE_TTL_BALANCED=1800   # 30 minutes

# Speed level (cheap, cache shorter)
TTS_CACHE_TTL_SPEED=600       # 10 minutes
```

### 3. Monitor Memory Usage
Redis stores data in RAM. Monitor usage:
- Free tier: Usually 30-100 MB
- Paid tier: 1 GB - 10+ GB

If running out of memory:
- Reduce TTL values
- Enable `maxmemory-policy allkeys-lru` (auto-evict old keys)
- Upgrade to larger plan

### 4. Database Numbers
Redis supports multiple databases (0-15):
```bash
REDIS_URL=redis://host:6379/0   # Database 0 (default)
REDIS_URL=redis://host:6379/1   # Database 1
```
Use different databases for dev/test/staging on same Redis instance.

---

## 📦 What Gets Cached?

### LLM Responses
**Cache Key Format:**
```
llm:exact:{hash}           # Exact query match
llm:semantic:{normalized}  # Semantic similarity match
llm:query_index           # Query index for similarity search
```

**Example:**
```
Query: "What is the weather?"
Cached for: 30 minutes (balanced)
Cache hit on: Exact same query or similar queries (if semantic enabled)
```

### TTS Audio
**Cache Key Format:**
```
tts:{provider}:{voice}:{text_hash}:{codec}
```

**Example:**
```
Provider: sarvam
Voice: meera
Text: "नमस्ते"
Codec: wav
Cached for: 15 minutes
```

---

## 🎯 Summary

1. **Get Redis connection string** from your provider
2. **Add to `.env`** as `REDIS_URL=...`
3. **Restart backend**
4. **Verify** in logs and metrics
5. **Enjoy** faster responses and lower costs!

**No Redis? No problem!** The app works fine without caching, just slower and more expensive.

---

## 📞 Need Help?

**Common Providers Documentation:**
- Redis Cloud: https://docs.redis.com/
- Upstash: https://docs.upstash.com/redis
- Railway: https://docs.railway.app/

**Redis Documentation:**
- Official: https://redis.io/docs/
- Connection Strings: https://redis.io/docs/manual/cli/
