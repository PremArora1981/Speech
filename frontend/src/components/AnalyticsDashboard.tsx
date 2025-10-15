import { BarChart3, Settings } from 'lucide-react';
import { useState } from 'react';
import { CostTracker } from './CostTracker';
import { SessionMetrics } from './SessionMetrics';
import { LatencyIndicator, createPipelineStages } from './LatencyIndicator';

type AnalyticsDashboardProps = {
  sessionId: string;
  optimizationLevel?: string;
  apiUrl?: string;
  apiKey?: string;
  className?: string;
};

export function AnalyticsDashboard({
  sessionId,
  optimizationLevel = 'balanced',
  apiUrl = 'http://localhost:8000/api/v1',
  apiKey = '',
  className = '',
}: AnalyticsDashboardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sessionId) {
    return null;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-neutral-100">
          <BarChart3 className="h-5 w-5 text-sky-400" />
          Analytics Dashboard
        </h2>
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-1.5 text-sm text-neutral-300 transition hover:bg-neutral-700"
        >
          <Settings className="h-4 w-4" />
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {/* Compact View */}
      {!isExpanded && (
        <div className="grid gap-4 lg:grid-cols-2">
          <CostTracker sessionId={sessionId} apiUrl={apiUrl} apiKey={apiKey} />
          <LatencyIndicator optimizationLevel={optimizationLevel} />
        </div>
      )}

      {/* Expanded View */}
      {isExpanded && (
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Left Column - Cost Tracking */}
          <div className="space-y-4">
            <CostTracker sessionId={sessionId} apiUrl={apiUrl} apiKey={apiKey} />
          </div>

          {/* Middle Column - Session Metrics */}
          <div className="lg:col-span-2">
            <SessionMetrics sessionId={sessionId} apiUrl={apiUrl} apiKey={apiKey} />
          </div>
        </div>
      )}

      {/* Session Info */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 px-4 py-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-500">Session ID</span>
          <span className="font-mono text-neutral-400">{sessionId}</span>
        </div>
      </div>
    </div>
  );
}

// Export individual components for standalone use
export { CostTracker } from './CostTracker';
export { SessionMetrics } from './SessionMetrics';
export { LatencyIndicator, createPipelineStages } from './LatencyIndicator';
export { FeedbackRating } from './FeedbackRating';
export { LanguageSelector } from './LanguageSelector';
