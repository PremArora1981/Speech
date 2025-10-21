import React, { useState } from 'react';
import { AlertTriangle, Gauge, Zap, TrendingUp } from 'lucide-react';

export type OptimizationLevel = 'quality' | 'balanced_quality' | 'balanced' | 'balanced_speed' | 'speed';

interface PerformanceSettingsProps {
  value: OptimizationLevel;
  onChange: (level: OptimizationLevel) => void;
  showDetailedMetrics?: boolean;
  className?: string;
}

const OPTIMIZATION_LEVELS: Array<{
  value: OptimizationLevel;
  label: string;
  accuracy: number;
  speed: number;
  expectedLatency: string;
  description: string;
  color: string;
}> = [
  {
    value: 'quality',
    label: 'Maximum Quality',
    accuracy: 95,
    speed: 20,
    expectedLatency: '15-25s',
    description: 'Best accuracy and response quality. Uses deep RAG search, semantic caching, and maximum model parameters.',
    color: 'from-green-500 to-emerald-600',
  },
  {
    value: 'balanced_quality',
    label: 'Balanced Quality',
    accuracy: 90,
    speed: 40,
    expectedLatency: '8-15s',
    description: 'High accuracy with improved speed. Uses moderate RAG retrieval and semantic similarity caching.',
    color: 'from-blue-500 to-cyan-600',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    accuracy: 85,
    speed: 60,
    expectedLatency: '5-8s',
    description: 'Optimal balance between quality and speed. Recommended for most use cases.',
    color: 'from-purple-500 to-violet-600',
  },
  {
    value: 'balanced_speed',
    label: 'Balanced Speed',
    accuracy: 75,
    speed: 80,
    expectedLatency: '3-5s',
    description: 'Prioritizes speed with acceptable quality. Uses limited RAG retrieval and aggressive caching.',
    color: 'from-orange-500 to-amber-600',
  },
  {
    value: 'speed',
    label: 'Maximum Speed',
    accuracy: 65,
    speed: 95,
    expectedLatency: '1-3s',
    description: 'Fastest response time. Skips RAG, uses cache warming, and optimizes for minimal latency.',
    color: 'from-red-500 to-pink-600',
  },
];

const CircularGauge: React.FC<{
  value: number;
  label: string;
  color: string;
  icon: React.ReactNode;
}> = ({ value, label, color, icon }) => {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div className="flex flex-col items-center space-y-2">
      <div className="relative w-32 h-32">
        {/* Background circle */}
        <svg className="transform -rotate-90 w-full h-full">
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Progress circle */}
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`${color} transition-all duration-500 ease-out`}
            strokeLinecap="round"
          />
        </svg>
        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-gray-500 dark:text-gray-400 mb-1">{icon}</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}%</div>
        </div>
      </div>
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</div>
    </div>
  );
};

export const PerformanceSettings: React.FC<PerformanceSettingsProps> = ({
  value,
  onChange,
  showDetailedMetrics = true,
  className = '',
}) => {
  const [selectedLevel, setSelectedLevel] = useState<OptimizationLevel>(value);

  const currentLevelIndex = OPTIMIZATION_LEVELS.findIndex((l) => l.value === selectedLevel);
  const currentLevel = OPTIMIZATION_LEVELS[currentLevelIndex];

  const handleChange = (newValue: number) => {
    const newLevel = OPTIMIZATION_LEVELS[newValue];
    setSelectedLevel(newLevel.value);
    onChange(newLevel.value);
  };

  const isExtreme = selectedLevel === 'quality' || selectedLevel === 'speed';

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Performance Settings
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Adjust the quality-latency tradeoff for your use case
          </p>
        </div>
        <button
          onClick={() => {
            setSelectedLevel('balanced');
            onChange('balanced');
          }}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Reset to Default
        </button>
      </div>

      {/* Optimization Level Slider */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Optimization Level
          </span>
          <span className={`text-sm font-semibold bg-gradient-to-r ${currentLevel.color} text-transparent bg-clip-text`}>
            {currentLevel.label}
          </span>
        </div>

        {/* Slider */}
        <div className="relative">
          <input
            type="range"
            min="0"
            max="4"
            step="1"
            value={currentLevelIndex}
            onChange={(e) => handleChange(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right,
                #10b981 0%, #10b981 ${(currentLevelIndex / 4) * 100}%,
                #e5e7eb ${(currentLevelIndex / 4) * 100}%, #e5e7eb 100%)`,
            }}
          />
          {/* Slider marks */}
          <div className="flex justify-between mt-2 px-1">
            {OPTIMIZATION_LEVELS.map((level, index) => (
              <button
                key={level.value}
                onClick={() => handleChange(index)}
                className={`text-xs transition-colors ${
                  index === currentLevelIndex
                    ? 'text-gray-900 dark:text-white font-semibold'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                title={level.label}
              >
                {level.label.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Description */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">{currentLevel.description}</p>
          <div className="mt-2 flex items-center space-x-4 text-xs text-gray-600 dark:text-gray-400">
            <span className="flex items-center">
              <TrendingUp className="w-3 h-3 mr-1" />
              Expected: {currentLevel.expectedLatency}
            </span>
          </div>
        </div>
      </div>

      {/* Warning for extreme settings */}
      {isExtreme && (
        <div className="flex items-start space-x-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              {selectedLevel === 'quality' ? 'High Latency Warning' : 'Quality Tradeoff Warning'}
            </h4>
            <p className="text-sm text-amber-800 dark:text-amber-300 mt-1">
              {selectedLevel === 'quality'
                ? 'This setting prioritizes accuracy over speed. Response times may be 15-25 seconds. Consider Balanced Quality for better user experience.'
                : 'This setting significantly reduces accuracy for speed. Response quality may be noticeably lower. Consider Balanced Speed for better results.'}
            </p>
          </div>
        </div>
      )}

      {/* Performance Gauges */}
      {showDetailedMetrics && (
        <div className="grid grid-cols-2 gap-6 pt-4">
          <CircularGauge
            value={currentLevel.accuracy}
            label="Accuracy"
            color="text-green-500"
            icon={<Gauge className="w-6 h-6" />}
          />
          <CircularGauge
            value={currentLevel.speed}
            label="Speed"
            color="text-blue-500"
            icon={<Zap className="w-6 h-6" />}
          />
        </div>
      )}

      {/* Preset Buttons (Optional) */}
      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => {
            setSelectedLevel('quality');
            onChange('quality');
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedLevel === 'quality'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-2 border-green-500'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Quality
        </button>
        <button
          onClick={() => {
            setSelectedLevel('balanced');
            onChange('balanced');
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedLevel === 'balanced'
              ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-2 border-purple-500'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Balanced
        </button>
        <button
          onClick={() => {
            setSelectedLevel('speed');
            onChange('speed');
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedLevel === 'speed'
              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-2 border-red-500'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          Speed
        </button>
      </div>

      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: linear-gradient(135deg, ${currentLevel.color.split(' ')[1].replace('to-', '')} 0%, ${currentLevel.color.split(' ')[2]} 100%);
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: linear-gradient(135deg, ${currentLevel.color.split(' ')[1].replace('to-', '')} 0%, ${currentLevel.color.split(' ')[2]} 100%);
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
      `}</style>
    </div>
  );
};

export default PerformanceSettings;
