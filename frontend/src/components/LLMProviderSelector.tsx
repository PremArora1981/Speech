import React, { useEffect, useState } from 'react';
import { fetchLLMProviders, fetchLLMModels } from '../lib/api';
import type { LLMProvider as APILLMProvider, LLMModel as APILLMModel } from '../lib/api';

// Re-export types
type LLMProvider = APILLMProvider;
type LLMModel = APILLMModel;

export type LLMConfig = {
  provider: string;
  model: string;
};

type LLMProviderSelectorProps = {
  value: LLMConfig;
  onChange: (config: LLMConfig) => void;
};

export const LLMProviderSelector: React.FC<LLMProviderSelectorProps> = ({ value, onChange }) => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  // Load models when provider changes
  useEffect(() => {
    if (value.provider) {
      loadModels(value.provider);
    }
  }, [value.provider]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchLLMProviders();
      setProviders(data);
    } catch (err) {
      setError('Failed to load LLM providers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async (provider: string) => {
    try {
      setError(null);
      const data = await fetchLLMModels(provider);
      setModels(data);
    } catch (err) {
      setError('Failed to load models');
      console.error(err);
    }
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value;
    onChange({
      provider: newProvider,
      model: '', // Reset model when provider changes
    });
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({
      ...value,
      model: e.target.value,
    });
  };

  const selectedModel = models.find((m) => m.id === value.model);

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded mb-4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <h3 className="text-lg font-semibold mb-4">LLM Configuration</h3>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Provider Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Provider
        </label>
        <select
          value={value.provider}
          onChange={handleProviderChange}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Select a provider</option>
          {providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.display_name} ({provider.model_count} models)
            </option>
          ))}
        </select>
        {value.provider && (
          <p className="mt-1 text-sm text-gray-500">
            {providers.find((p) => p.id === value.provider)?.description}
          </p>
        )}
      </div>

      {/* Model Selection */}
      {value.provider && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Model
          </label>
          <select
            value={value.model}
            onChange={handleModelChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a model</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Model Details */}
      {selectedModel && (
        <div className="mt-4 p-4 bg-gray-50 rounded-md">
          <h4 className="font-medium text-gray-900 mb-2">{selectedModel.name}</h4>
          {selectedModel.description && (
            <p className="text-sm text-gray-600 mb-3">{selectedModel.description}</p>
          )}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="font-medium text-gray-700">Context Window:</span>
              <span className="ml-2 text-gray-600">
                {selectedModel.context_window.toLocaleString()} tokens
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Max Output:</span>
              <span className="ml-2 text-gray-600">
                {selectedModel.max_output_tokens.toLocaleString()} tokens
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Input Cost:</span>
              <span className="ml-2 text-gray-600">
                ${selectedModel.cost_per_1k_input_tokens.toFixed(4)}/1K tokens
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Output Cost:</span>
              <span className="ml-2 text-gray-600">
                ${selectedModel.cost_per_1k_output_tokens.toFixed(4)}/1K tokens
              </span>
            </div>
            {selectedModel.supports_streaming && (
              <div className="col-span-2">
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                  Streaming Supported
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
