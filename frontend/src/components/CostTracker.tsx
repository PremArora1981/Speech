import { DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';

type CostSummary = {
  total_cost_usd: number;
  breakdown_by_service: {
    asr?: number;
    llm?: number;
    translation?: number;
    tts?: number;
  };
  breakdown_by_provider: {
    sarvam?: number;
    openai?: number;
    elevenlabs?: number;
  };
  total_entries: number;
  cache_savings_usd: number;
  optimization_level: string | null;
};

type CostTrackerProps = {
  sessionId: string;
  apiUrl?: string;
  apiKey?: string;
  refreshInterval?: number;
};

const formatCurrency = (amount: number): string => {
  if (amount === 0) return '$0.0000';
  if (amount < 0.0001) return '<$0.0001';
  return `$${amount.toFixed(4)}`;
};

export function CostTracker({
  sessionId,
  apiUrl = 'http://localhost:8000/api/v1',
  apiKey = '',
  refreshInterval = 5000,
}: CostTrackerProps) {
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }

    const fetchCostSummary = async () => {
      try {
        const response = await fetch(`${apiUrl}/sessions/${sessionId}/costs`, {
          headers: {
            'X-API-Key': apiKey,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch cost summary: ${response.statusText}`);
        }

        const data = (await response.json()) as CostSummary;
        setCostSummary(data);
        setError(null);
      } catch (err) {
        console.error('Cost tracking error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load cost data');
      } finally {
        setLoading(false);
      }
    };

    void fetchCostSummary();

    const interval = setInterval(() => {
      void fetchCostSummary();
    }, refreshInterval);

    return () => {
      clearInterval(interval);
    };
  }, [sessionId, apiUrl, apiKey, refreshInterval]);

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <DollarSign className="h-4 w-4 animate-pulse" />
          <span>Loading cost data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4">
        <div className="flex items-center gap-2 text-sm text-red-300">
          <DollarSign className="h-4 w-4" />
          <span>Cost tracking unavailable</span>
        </div>
      </div>
    );
  }

  if (!costSummary || costSummary.total_entries === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-500">
          <DollarSign className="h-4 w-4" />
          <span>No cost data yet</span>
        </div>
      </div>
    );
  }

  const savingsPercent =
    costSummary.total_cost_usd > 0
      ? (costSummary.cache_savings_usd / (costSummary.total_cost_usd + costSummary.cache_savings_usd)) * 100
      : 0;

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 shadow-lg">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-100">
          <DollarSign className="h-4 w-4 text-emerald-400" />
          Session Cost
        </h3>
        {costSummary.optimization_level && (
          <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-300">
            {costSummary.optimization_level}
          </span>
        )}
      </div>

      {/* Total Cost */}
      <div className="mb-4">
        <div className="text-2xl font-bold text-emerald-400">{formatCurrency(costSummary.total_cost_usd)}</div>
        <div className="text-xs text-neutral-500">{costSummary.total_entries} API calls</div>
      </div>

      {/* Service Breakdown */}
      <div className="mb-4 space-y-2">
        <div className="text-xs font-medium uppercase text-neutral-400">By Service</div>
        {Object.entries(costSummary.breakdown_by_service).map(([service, cost]) => (
          <div key={service} className="flex items-center justify-between text-sm">
            <span className="capitalize text-neutral-300">{service}</span>
            <span className="font-mono text-neutral-100">{formatCurrency(cost)}</span>
          </div>
        ))}
      </div>

      {/* Provider Breakdown */}
      <div className="mb-4 space-y-2">
        <div className="text-xs font-medium uppercase text-neutral-400">By Provider</div>
        {Object.entries(costSummary.breakdown_by_provider).map(([provider, cost]) => (
          <div key={provider} className="flex items-center justify-between text-sm">
            <span className="capitalize text-neutral-300">{provider}</span>
            <span className="font-mono text-neutral-100">{formatCurrency(cost)}</span>
          </div>
        ))}
      </div>

      {/* Cache Savings */}
      {costSummary.cache_savings_usd > 0 && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-green-400" />
              <span className="text-xs font-medium text-green-300">Cache Savings</span>
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-green-400">{formatCurrency(costSummary.cache_savings_usd)}</div>
              <div className="text-xs text-green-300">{savingsPercent.toFixed(1)}% saved</div>
            </div>
          </div>
        </div>
      )}

      {/* Low savings or no caching */}
      {costSummary.cache_savings_usd === 0 && costSummary.total_cost_usd > 0.01 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-amber-400" />
            <span className="text-xs text-amber-300">Enable caching to reduce costs</span>
          </div>
        </div>
      )}
    </div>
  );
}
