import React, { useState, useEffect } from 'react';
import { Settings, Save, Download, Upload, RotateCcw } from 'lucide-react';
import { LLMProviderSelector, LLMConfig } from './LLMProviderSelector';
import { DynamicVoiceGallery, VoiceConfig } from './DynamicVoiceGallery';
import { SystemPromptEditor } from './SystemPromptEditor';
import { LanguageSelector } from './LanguageSelector';
import {
  fetchSessionConfigurations,
  fetchSessionConfiguration,
  createSessionConfiguration,
  SessionConfiguration,
} from '../lib/api';

export type SessionConfig = {
  // LLM Configuration
  llm: LLMConfig;

  // Voice Configuration
  voice: VoiceConfig;

  // System Prompt
  systemPromptId: string;
  systemPromptText: string;

  // Other Settings
  optimizationLevel: string;
  targetLanguage: string;
  enableRAG: boolean;
};

type ConfigurationPanelProps = {
  value: SessionConfig;
  onChange: (config: SessionConfig) => void;
  onSave?: (config: SessionConfig) => void;
  onLoad?: () => void;
  className?: string;
};

export const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({
  value,
  onChange,
  onSave,
  onLoad,
  className,
}) => {
  const [activeTab, setActiveTab] = useState<'llm' | 'voice' | 'prompt' | 'advanced'>('llm');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [configName, setConfigName] = useState('');
  const [configDescription, setConfigDescription] = useState('');
  const [savedConfigs, setSavedConfigs] = useState<SessionConfiguration[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);

  // Load saved configurations on mount
  useEffect(() => {
    loadSavedConfigurations();
  }, []);

  const loadSavedConfigurations = async () => {
    setLoadingConfigs(true);
    try {
      const configs = await fetchSessionConfigurations();
      setSavedConfigs(configs);
    } catch (error) {
      console.error('Failed to load configurations:', error);
    } finally {
      setLoadingConfigs(false);
    }
  };

  const handleLLMChange = (llm: LLMConfig) => {
    onChange({ ...value, llm });
  };

  const handleVoiceChange = (voice: VoiceConfig) => {
    onChange({ ...value, voice });
  };

  const handlePromptChange = (promptId: string, promptText: string) => {
    onChange({
      ...value,
      systemPromptId: promptId,
      systemPromptText: promptText,
    });
  };

  const handleOptimizationChange = (optimizationLevel: string) => {
    onChange({ ...value, optimizationLevel });
  };

  const handleLanguageChange = (targetLanguage: string) => {
    onChange({ ...value, targetLanguage });
  };

  const handleLoadConfiguration = async (configId: string) => {
    if (!configId) return;

    try {
      const config = await fetchSessionConfiguration(configId);

      // Apply loaded configuration
      onChange({
        llm: {
          provider: config.llm_provider,
          model: config.llm_model,
        },
        voice: {
          provider: config.tts_provider,
          voice_id: config.tts_voice_id,
          display_name: config.tts_voice_id, // Will be updated by voice selector
          tuning: config.voice_tuning || {},
        },
        systemPromptId: config.system_prompt_id || '',
        systemPromptText: config.system_prompt_text || '',
        optimizationLevel: config.optimization_level,
        targetLanguage: config.target_language,
        enableRAG: config.enable_rag || false,
      });

      alert(`Configuration "${config.name}" loaded successfully!`);
    } catch (error) {
      console.error('Failed to load configuration:', error);
      alert('Failed to load configuration. Please try again.');
    }
  };

  const handleSaveConfiguration = async () => {
    if (!configName.trim()) {
      alert('Please enter a configuration name.');
      return;
    }

    setSavingConfig(true);
    try {
      const savedConfig = await createSessionConfiguration({
        name: configName.trim(),
        description: configDescription.trim() || undefined,
        llm_provider: value.llm.provider,
        llm_model: value.llm.model,
        tts_provider: value.voice.provider,
        tts_voice_id: value.voice.voice_id,
        voice_tuning: value.voice.tuning,
        system_prompt_id: value.systemPromptId || undefined,
        system_prompt_text: value.systemPromptText,
        optimization_level: value.optimizationLevel,
        target_language: value.targetLanguage,
        enable_rag: value.enableRAG,
        is_default: false,
      });

      alert(`Configuration "${savedConfig.name}" saved successfully!`);
      
      // Reload configurations list
      await loadSavedConfigurations();
      
      // Close dialog and reset form
      setShowSaveDialog(false);
      setConfigName('');
      setConfigDescription('');

      if (onSave) {
        onSave(value);
      }
    } catch (error) {
      console.error('Failed to save configuration:', error);
      alert('Failed to save configuration. Please try again.');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleExportConfig = () => {
    const configJSON = JSON.stringify(value, null, 2);
    const blob = new Blob([configJSON], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `voice-config-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportConfig = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    input.onchange = async (e: any) => {
      const file = e.target.files[0];
      if (file) {
        const text = await file.text();
        try {
          const config = JSON.parse(text);
          onChange(config);
        } catch (err) {
          alert('Failed to import configuration. Invalid JSON file.');
        }
      }
    };
    input.click();
  };

  const handleReset = () => {
    if (confirm('Reset to default configuration?')) {
      onChange({
        llm: { provider: 'sarvam', model: 'sarvam-1' },
        voice: {
          provider: 'sarvam',
          voice_id: 'anushka',
          display_name: 'Anushka',
          tuning: {},
        },
        systemPromptId: '',
        systemPromptText: 'You are a helpful AI assistant.',
        optimizationLevel: 'balanced',
        targetLanguage: 'en-IN',
        enableRAG: false,
      });
    }
  };

  const tabs = [
    { id: 'llm', label: 'LLM Settings', icon: '🤖' },
    { id: 'voice', label: 'Voice Settings', icon: '🎤' },
    { id: 'prompt', label: 'System Prompt', icon: '📝' },
    { id: 'advanced', label: 'Advanced', icon: '⚙️' },
  ] as const;

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className || ''}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-700" />
            <h2 className="text-xl font-semibold text-gray-900">Configuration</h2>
          </div>
          <div className="flex gap-2">
            {/* Load Configuration Dropdown */}
            <select
              onChange={(e) => handleLoadConfiguration(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              disabled={loadingConfigs}
            >
              <option value="">
                {loadingConfigs ? 'Loading...' : 'Load Configuration...'}
              </option>
              {savedConfigs.map((config) => (
                <option key={config.id} value={config.id}>
                  {config.name}
                </option>
              ))}
            </select>

            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              title="Reset to Defaults"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            <button
              onClick={handleImportConfig}
              className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              title="Import Configuration"
            >
              <Upload className="w-4 h-4" />
              Import
            </button>
            <button
              onClick={handleExportConfig}
              className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
              title="Export Configuration"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            {onSave && (
              <button
                onClick={() => setShowSaveDialog(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md"
              >
                <Save className="w-4 h-4" />
                Save
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-1 p-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'llm' && (
          <LLMProviderSelector value={value.llm} onChange={handleLLMChange} />
        )}

        {activeTab === 'voice' && (
          <DynamicVoiceGallery
            value={value.voice}
            onChange={handleVoiceChange}
            provider={value.voice.provider}
          />
        )}

        {activeTab === 'prompt' && (
          <SystemPromptEditor
            value={value.systemPromptText}
            onChange={handlePromptChange}
          />
        )}

        {activeTab === 'advanced' && (
          <div className="space-y-6">
            {/* Optimization Level */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Optimization Level</h3>
              <select
                value={value.optimizationLevel}
                onChange={(e) => handleOptimizationChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="quality">Quality (Highest accuracy, slower)</option>
                <option value="balanced_quality">Balanced Quality</option>
                <option value="balanced">Balanced (Recommended)</option>
                <option value="balanced_speed">Balanced Speed</option>
                <option value="speed">Speed (Fastest, lower accuracy)</option>
              </select>
              <p className="mt-2 text-sm text-gray-600">
                Choose the trade-off between quality and speed
              </p>
            </div>

            {/* Target Language */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">Target Language</h3>
              <LanguageSelector
                value={value.targetLanguage}
                onChange={handleLanguageChange}
              />
            </div>

            {/* RAG Settings */}
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">RAG (Retrieval-Augmented Generation)</h3>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={value.enableRAG}
                  onChange={(e) => onChange({ ...value, enableRAG: e.target.checked })}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Enable RAG context augmentation
                </span>
              </label>
              <p className="mt-2 text-sm text-gray-600">
                Use document retrieval to enhance LLM responses with relevant context
              </p>
            </div>

            {/* Configuration Summary */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold mb-3">Configuration Summary</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">LLM Provider:</span>
                  <span className="font-medium">{value.llm.provider || 'Not selected'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">LLM Model:</span>
                  <span className="font-medium">{value.llm.model || 'Not selected'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Voice Provider:</span>
                  <span className="font-medium">{value.voice.provider}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Voice:</span>
                  <span className="font-medium">{value.voice.display_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Optimization:</span>
                  <span className="font-medium">{value.optimizationLevel}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Language:</span>
                  <span className="font-medium">{value.targetLanguage}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">RAG Enabled:</span>
                  <span className="font-medium">{value.enableRAG ? 'Yes' : 'No'}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Save Configuration</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Configuration Name *
              </label>
              <input
                type="text"
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
                placeholder="My Custom Configuration"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                value={configDescription}
                onChange={(e) => setConfigDescription(e.target.value)}
                placeholder="Configuration description..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setConfigName('');
                  setConfigDescription('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={savingConfig}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveConfiguration}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
                disabled={savingConfig || !configName.trim()}
              >
                {savingConfig ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
