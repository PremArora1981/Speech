import { Activity, Clock, Shield, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';

type Metrics = {
  total_turns: number;
  successful_turns: number;
  failed_turns: number;
  interrupted_turns: number;
  avg_asr_latency_ms: number | null;
  avg_llm_latency_ms: number | null;
  avg_translation_latency_ms: number | null;
  avg_tts_latency_ms: number | null;
  avg_total_latency_ms: number | null;
  cache_hit_rate: number | null;
  llm_cache_hits: number;
  llm_cache_misses: number;
  tts_cache_hits: number;
  tts_cache_misses: number;
  guardrail_violations: number;
  guardrail_blocks: number;
  total_cost_usd: number;
  optimization_level: string | null;
  language_code: string | null;
};

type SessionMetricsProps = {
  sessionId: string;
  apiUrl?: string;
  apiKey?: string;
  refreshInterval?: number;
};

const formatLatency = (ms: number | null): string => {
  if (ms === null || ms === 0) return '-';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

const formatPercent = (value: number | null): string => {
  if (value === null) return '-';
  return `${(value * 100).toFixed(1)}%`;
};

export function SessionMetrics({
  sessionId,
  apiUrl = 'http://localhost:8000/api/v1',
  apiKey = '',
  refreshInterval = 3000,
}: SessionMetricsProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }

    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${apiUrl}/sessions/${sessionId}/metrics`, {
          headers: {
            'X-API-Key': apiKey,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch metrics: ${response.statusText}`);
        }

        const data = (await response.json()) as Metrics;
        setMetrics(data);
        setError(null);
      } catch (err) {
        console.error('Metrics error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load metrics');
      } finally {
        setLoading(false);
      }
    };

    void fetchMetrics();

    const interval = setInterval(() => {
      void fetchMetrics();
    }, refreshInterval);

    return () => {
      clearInterval(interval);
    };
  }, [sessionId, apiUrl, apiKey, refreshInterval]);

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <Activity className="h-4 w-4 animate-pulse" />
          <span>Loading metrics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4">
        <div className="flex items-center gap-2 text-sm text-red-300">
          <Activity className="h-4 w-4" />
          <span>Metrics unavailable</span>
        </div>
      </div>
    );
  }

  if (!metrics || metrics.total_turns === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <Activity className="h-4 w-4" />
          <span>No metrics yet</span>
        </div>
      </div>
    );
  }

  const successRate = metrics.total_turns > 0 ? (metrics.successful_turns / metrics.total_turns) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 shadow-lg">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-100">
            <Activity className="h-4 w-4 text-sky-400" />
            Session Metrics
          </h3>
          {metrics.optimization_level && (
            <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-300">
              {metrics.optimization_level}
            </span>
          )}
        </div>

        {/* Turn Statistics */}
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-neutral-500">Total Turns</div>
            <div className="text-xl font-bold text-neutral-100">{metrics.total_turns}</div>
          </div>
          <div>
            <div className="text-xs text-neutral-500">Success Rate</div>
            <div
              className={`text-xl font-bold ${successRate >= 90 ? 'text-emerald-400' : successRate >= 70 ? 'text-amber-400' : 'text-red-400'}`}
            >
              {successRate.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Turn Breakdown */}
        <div className="mb-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">Successful</span>
            <span className="font-mono text-emerald-400">{metrics.successful_turns}</span>
          </div>
          {metrics.failed_turns > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Failed</span>
              <span className="font-mono text-red-400">{metrics.failed_turns}</span>
            </div>
          )}
          {metrics.interrupted_turns > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-400">Interrupted</span>
              <span className="font-mono text-amber-400">{metrics.interrupted_turns}</span>
            </div>
          )}
        </div>
      </div>

      {/* Latency Card */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 shadow-lg">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-100">
          <Clock className="h-4 w-4 text-sky-400" />
          Average Latency
        </h4>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">ASR</span>
            <span className="font-mono text-neutral-100">{formatLatency(metrics.avg_asr_latency_ms)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">LLM</span>
            <span className="font-mono text-neutral-100">{formatLatency(metrics.avg_llm_latency_ms)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">Translation</span>
            <span className="font-mono text-neutral-100">{formatLatency(metrics.avg_translation_latency_ms)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">TTS</span>
            <span className="font-mono text-neutral-100">{formatLatency(metrics.avg_tts_latency_ms)}</span>
          </div>
          {metrics.avg_total_latency_ms !== null && (
            <div className="mt-2 flex items-center justify-between border-t border-neutral-800 pt-2 text-sm font-semibold">
              <span className="text-neutral-300">Total</span>
              <span className="font-mono text-emerald-400">{formatLatency(metrics.avg_total_latency_ms)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Cache Performance */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 shadow-lg">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-100">
          <Zap className="h-4 w-4 text-amber-400" />
          Cache Performance
        </h4>
        <div className="mb-3">
          <div className="text-xs text-neutral-500">Hit Rate</div>
          <div
            className={`text-xl font-bold ${
              (metrics.cache_hit_rate ?? 0) >= 0.7
                ? 'text-emerald-400'
                : (metrics.cache_hit_rate ?? 0) >= 0.4
                  ? 'text-amber-400'
                  : 'text-red-400'
            }`}
          >
            {formatPercent(metrics.cache_hit_rate)}
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">LLM Hits</span>
            <span className="font-mono text-emerald-400">{metrics.llm_cache_hits}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">LLM Misses</span>
            <span className="font-mono text-neutral-500">{metrics.llm_cache_misses}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">TTS Hits</span>
            <span className="font-mono text-emerald-400">{metrics.tts_cache_hits}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">TTS Misses</span>
            <span className="font-mono text-neutral-500">{metrics.tts_cache_misses}</span>
          </div>
        </div>
      </div>

      {/* Guardrails */}
      {(metrics.guardrail_violations > 0 || metrics.guardrail_blocks > 0) && (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 shadow-lg">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-300">
            <Shield className="h-4 w-4" />
            Guardrail Activity
          </h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-amber-200">Violations</span>
              <span className="font-mono text-amber-400">{metrics.guardrail_violations}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-amber-200">Blocks</span>
              <span className="font-mono text-amber-400">{metrics.guardrail_blocks}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
