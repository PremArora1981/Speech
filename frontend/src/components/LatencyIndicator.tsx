import { Clock, Zap } from 'lucide-react';

type LatencyStage = {
  name: string;
  duration: number;
  color: string;
};

type LatencyIndicatorProps = {
  stages?: LatencyStage[];
  totalLatency?: number;
  optimizationLevel?: string;
  className?: string;
};

const formatDuration = (ms: number): string => {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

const getLatencyColor = (ms: number, optimizationLevel: string): string => {
  // Thresholds vary by optimization level
  const thresholds = {
    quality: { good: 4000, ok: 6000 },
    balanced_quality: { good: 3000, ok: 4500 },
    balanced: { good: 2000, ok: 3000 },
    balanced_speed: { good: 1500, ok: 2500 },
    speed: { good: 1000, ok: 1500 },
  };

  const threshold = thresholds[optimizationLevel as keyof typeof thresholds] ?? thresholds.balanced;

  if (ms <= threshold.good) return 'text-emerald-400';
  if (ms <= threshold.ok) return 'text-amber-400';
  return 'text-red-400';
};

export function LatencyIndicator({
  stages = [],
  totalLatency,
  optimizationLevel = 'balanced',
  className = '',
}: LatencyIndicatorProps) {
  const total = totalLatency ?? stages.reduce((sum, stage) => sum + stage.duration, 0);

  if (total === 0 && stages.length === 0) {
    return null;
  }

  const latencyColor = getLatencyColor(total, optimizationLevel);

  return (
    <div className={`rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 ${className}`}>
      {/* Total Latency */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-neutral-400">
          <Clock className="h-3.5 w-3.5" />
          <span>Total Latency</span>
        </div>
        <div className={`text-sm font-bold ${latencyColor}`}>{formatDuration(total)}</div>
      </div>

      {/* Stage Breakdown */}
      {stages.length > 0 && (
        <div className="space-y-1.5">
          {stages.map((stage, index) => {
            const percentage = total > 0 ? (stage.duration / total) * 100 : 0;
            return (
              <div key={`${stage.name}-${index}`} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-500">{stage.name}</span>
                  <span className="font-mono text-neutral-300">{formatDuration(stage.duration)}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
                  <div
                    className={`h-full ${stage.color}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Optimization Level Badge */}
      <div className="mt-2 flex items-center gap-1.5 text-xs text-neutral-500">
        <Zap className="h-3 w-3" />
        <span className="capitalize">{optimizationLevel.replace('_', ' ')}</span>
      </div>
    </div>
  );
}

// Preset stage configurations for common pipelines
export const createPipelineStages = (
  asrMs: number,
  llmMs: number,
  translationMs: number,
  ttsMs: number,
): LatencyStage[] => [
  { name: 'ASR', duration: asrMs, color: 'bg-blue-500' },
  { name: 'LLM', duration: llmMs, color: 'bg-purple-500' },
  { name: 'Translation', duration: translationMs, color: 'bg-green-500' },
  { name: 'TTS', duration: ttsMs, color: 'bg-amber-500' },
];
