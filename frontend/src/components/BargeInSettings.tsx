import React, { useState } from 'react';
import { Mic, MicOff, Volume2, Clock, RotateCcw, Info } from 'lucide-react';

export interface BargeInConfig {
  enabled: boolean;
  vadSensitivity: number; // 0-1 scale
  minSpeechDuration: number; // milliseconds
  interruptionDelay: number; // milliseconds (0-500)
  resumeAfterFalsePositive: boolean;
}

interface BargeInSettingsProps {
  value: BargeInConfig;
  onChange: (config: BargeInConfig) => void;
  className?: string;
}

const DEFAULT_CONFIG: BargeInConfig = {
  enabled: true,
  vadSensitivity: 0.7,
  minSpeechDuration: 300,
  interruptionDelay: 100,
  resumeAfterFalsePositive: true,
};

export const BargeInSettings: React.FC<BargeInSettingsProps> = ({
  value,
  onChange,
  className = '',
}) => {
  const [config, setConfig] = useState<BargeInConfig>(value);

  const updateConfig = (updates: Partial<BargeInConfig>) => {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    onChange(newConfig);
  };

  const resetToDefaults = () => {
    setConfig(DEFAULT_CONFIG);
    onChange(DEFAULT_CONFIG);
  };

  const getSensitivityLabel = (value: number): string => {
    if (value < 0.3) return 'Very Low (Rare interruptions)';
    if (value < 0.5) return 'Low (Conservative)';
    if (value < 0.7) return 'Medium (Balanced)';
    if (value < 0.9) return 'High (Responsive)';
    return 'Very High (Aggressive)';
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Barge-In Settings
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Configure voice activity detection and interruption behavior
          </p>
        </div>
        <button
          onClick={resetToDefaults}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset</span>
        </button>
      </div>

      {/* Enable/Disable Toggle */}
      <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
        <div className="flex items-center space-x-3">
          {config.enabled ? (
            <Mic className="w-5 h-5 text-green-600 dark:text-green-400" />
          ) : (
            <MicOff className="w-5 h-5 text-gray-400" />
          )}
          <div>
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              Enable Barge-In
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Allow users to interrupt AI responses
            </div>
          </div>
        </div>
        <button
          onClick={() => updateConfig({ enabled: !config.enabled })}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            config.enabled ? 'bg-green-600' : 'bg-gray-300 dark:bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              config.enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Settings (only visible when enabled) */}
      {config.enabled && (
        <div className="space-y-6">
          {/* VAD Sensitivity */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Volume2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Voice Activity Sensitivity
                </span>
              </div>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {(config.vadSensitivity * 100).toFixed(0)}%
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={config.vadSensitivity}
              onChange={(e) => updateConfig({ vadSensitivity: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />

            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Less Sensitive</span>
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {getSensitivityLabel(config.vadSensitivity)}
              </span>
              <span>More Sensitive</span>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
              <div className="flex items-start space-x-2">
                <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-800 dark:text-blue-300">
                  {config.vadSensitivity < 0.5
                    ? 'Low sensitivity reduces false interruptions but may miss soft speech.'
                    : config.vadSensitivity < 0.8
                    ? 'Balanced sensitivity works well in most environments.'
                    : 'High sensitivity responds quickly but may trigger on background noise.'}
                </p>
              </div>
            </div>
          </div>

          {/* Minimum Speech Duration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Minimum Speech Duration
                </span>
              </div>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {config.minSpeechDuration}ms
              </span>
            </div>

            <input
              type="range"
              min="100"
              max="1000"
              step="50"
              value={config.minSpeechDuration}
              onChange={(e) => updateConfig({ minSpeechDuration: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />

            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>100ms (Quick)</span>
              <span>500ms (Balanced)</span>
              <span>1000ms (Deliberate)</span>
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-400">
              How long user must speak before triggering interruption. Higher values reduce false
              positives.
            </p>
          </div>

          {/* Interruption Delay */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Interruption Delay
                </span>
              </div>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {config.interruptionDelay}ms
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="500"
              step="50"
              value={config.interruptionDelay}
              onChange={(e) => updateConfig({ interruptionDelay: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />

            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>0ms (Instant)</span>
              <span>250ms (Moderate)</span>
              <span>500ms (Patient)</span>
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-400">
              Delay before stopping AI playback after detecting speech. Allows brief overlaps.
            </p>
          </div>

          {/* Resume After False Positive */}
          <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                Resume After False Trigger
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Automatically resume playback if no follow-up speech detected
              </div>
            </div>
            <button
              onClick={() =>
                updateConfig({ resumeAfterFalsePositive: !config.resumeAfterFalsePositive })
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.resumeAfterFalsePositive ? 'bg-green-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.resumeAfterFalsePositive ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Test Barge-In (Placeholder for future implementation) */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <button
              className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
              onClick={() => {
                // This would trigger a test mode where user can speak and see real-time VAD feedback
                alert('Test mode would show live voice activity detection feedback');
              }}
            >
              <Mic className="w-4 h-4" />
              <span>Test Barge-In Settings</span>
            </button>
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-2">
              Speak to see real-time voice activity detection
            </p>
          </div>
        </div>
      )}

      {/* Disabled State Message */}
      {!config.enabled && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 text-center">
          <MicOff className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Barge-in is currently disabled. Users cannot interrupt AI responses.
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
            Enable to allow natural conversation flow with interruptions.
          </p>
        </div>
      )}
    </div>
  );
};

export default BargeInSettings;
