-- Migration: Add analytics and monitoring tables
-- Date: 2025-10-15
-- Description: Adds tables for guardrail violations, enhanced cost tracking, session metrics, user feedback, and turn events

-- 1. Guardrail Violations Table
CREATE TABLE IF NOT EXISTS guardrail_violations (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES sessions(id),
    turn_id VARCHAR,
    violation_type VARCHAR(50) NOT NULL,
    layer INTEGER NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    violated_rule VARCHAR(100) NOT NULL,
    input_text TEXT,
    output_text TEXT,
    safe_response TEXT,
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_guardrail_session_created ON guardrail_violations(session_id, created_at);
CREATE INDEX ix_guardrail_type_created ON guardrail_violations(violation_type, created_at);
CREATE INDEX ix_guardrail_severity_created ON guardrail_violations(severity, created_at);

-- 2. Enhanced Cost Entries Table
CREATE TABLE IF NOT EXISTS cost_entries (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES sessions(id),
    turn_id VARCHAR,
    service VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    units INTEGER NOT NULL,
    unit_type VARCHAR(20) NOT NULL,
    cost_usd NUMERIC(10, 6) NOT NULL,
    optimization_level VARCHAR(32),
    cached BOOLEAN DEFAULT FALSE,
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_cost_session_created ON cost_entries(session_id, created_at);
CREATE INDEX ix_cost_service_created ON cost_entries(service, created_at);
CREATE INDEX ix_cost_provider_created ON cost_entries(provider, created_at);

-- 3. Session Metrics Table
CREATE TABLE IF NOT EXISTS session_metrics (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES sessions(id) UNIQUE NOT NULL,

    -- Turn counts
    total_turns INTEGER DEFAULT 0,
    successful_turns INTEGER DEFAULT 0,
    failed_turns INTEGER DEFAULT 0,
    interrupted_turns INTEGER DEFAULT 0,

    -- Latency metrics (milliseconds)
    avg_asr_latency_ms FLOAT,
    avg_llm_latency_ms FLOAT,
    avg_translation_latency_ms FLOAT,
    avg_tts_latency_ms FLOAT,
    avg_total_latency_ms FLOAT,

    -- Cache metrics
    cache_hit_rate FLOAT,
    llm_cache_hits INTEGER DEFAULT 0,
    llm_cache_misses INTEGER DEFAULT 0,
    tts_cache_hits INTEGER DEFAULT 0,
    tts_cache_misses INTEGER DEFAULT 0,

    -- Guardrail metrics
    guardrail_violations INTEGER DEFAULT 0,
    guardrail_blocks INTEGER DEFAULT 0,

    -- Cost metrics
    total_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    asr_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    llm_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    translation_cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    tts_cost_usd NUMERIC(10, 6) DEFAULT 0.0,

    -- Quality metrics
    avg_asr_confidence FLOAT,
    avg_user_satisfaction FLOAT,

    -- Session info
    optimization_level VARCHAR(32),
    language_code VARCHAR(10),
    session_duration_seconds INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_metrics_created ON session_metrics(created_at);
CREATE INDEX ix_metrics_optimization ON session_metrics(optimization_level, created_at);

-- 4. User Feedback Table
CREATE TABLE IF NOT EXISTS user_feedback (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES sessions(id) NOT NULL,
    turn_id VARCHAR,
    message_id VARCHAR REFERENCES messages(id),

    -- Rating
    rating INTEGER NOT NULL,
    rating_type VARCHAR(20) NOT NULL DEFAULT 'thumbs',

    -- Feedback details
    feedback_text TEXT,
    feedback_category VARCHAR(50),

    -- Issue flags
    incorrect_response BOOLEAN DEFAULT FALSE,
    too_slow BOOLEAN DEFAULT FALSE,
    unhelpful BOOLEAN DEFAULT FALSE,
    offensive BOOLEAN DEFAULT FALSE,

    -- Context
    user_input TEXT,
    assistant_response TEXT,
    metadata JSON DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_feedback_session_created ON user_feedback(session_id, created_at);
CREATE INDEX ix_feedback_rating_created ON user_feedback(rating, created_at);

-- 5. Turn Events Table
CREATE TABLE IF NOT EXISTS turn_events (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES sessions(id) NOT NULL,
    turn_id VARCHAR NOT NULL,

    -- Event details
    event_type VARCHAR(50) NOT NULL,
    event_status VARCHAR(20) NOT NULL,
    stage VARCHAR(20) NOT NULL,

    -- Timing
    latency_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Result data
    result_data JSON DEFAULT '{}',
    error_message TEXT,

    -- Performance
    tokens_used INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_turn_session_turn ON turn_events(session_id, turn_id, timestamp);
CREATE INDEX ix_turn_event_type ON turn_events(event_type, created_at);
