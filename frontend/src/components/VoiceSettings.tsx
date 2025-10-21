import React, { useState } from 'react';
import { Play, Volume2, Mic, Loader2, Check } from 'lucide-react';

export type TTSProvider = 'sarvam' | 'elevenlabs';

export interface Voice {
  id: string;
  name: string;
  provider: TTSProvider;
  language: string;
  gender: 'male' | 'female' | 'neutral';
  characteristics: string[];
  previewText: string;
}

export interface VoiceTuning {
  pitch?: number; // -0.75 to 0.75 (Sarvam only)
  speed?: number; // 0.3 to 3.0 (Sarvam only)
  volume?: number; // 0 to 3.0 (Sarvam only)
}

export interface VoiceConfig {
  selectedVoice: Voice;
  tuning: VoiceTuning;
}

interface VoiceSettingsProps {
  value: VoiceConfig;
  onChange: (config: VoiceConfig) => void;
  onPreview?: (voice: Voice, customText?: string, tuning?: VoiceTuning) => Promise<void>;
  className?: string;
}

// Sample voice catalog (in production, fetch from backend)
const VOICE_CATALOG: Voice[] = [
  // Sarvam Voices
  {
    id: 'meera',
    name: 'Meera',
    provider: 'sarvam',
    language: 'hi-IN',
    gender: 'female',
    characteristics: ['Warm', 'Professional', 'Clear'],
    previewText: 'नमस्ते, मैं मीरा हूं। मैं आपकी कैसे मदद कर सकती हूं?',
  },
  {
    id: 'arjun',
    name: 'Arjun',
    provider: 'sarvam',
    language: 'hi-IN',
    gender: 'male',
    characteristics: ['Confident', 'Friendly', 'Energetic'],
    previewText: 'नमस्ते, मैं अर्जुन हूं। आपका स्वागत है।',
  },
  {
    id: 'priya',
    name: 'Priya',
    provider: 'sarvam',
    language: 'ta-IN',
    gender: 'female',
    characteristics: ['Soft', 'Melodic', 'Patient'],
    previewText: 'வணக்கம், நான் பிரியா. உங்களுக்கு எப்படி உதவ முடியும்?',
  },
  {
    id: 'raj',
    name: 'Raj',
    provider: 'sarvam',
    language: 'te-IN',
    gender: 'male',
    characteristics: ['Calm', 'Articulate', 'Respectful'],
    previewText: 'నమస్కారం, నేను రాజ్. మీకు ఎలా సహాయం చేయగలను?',
  },
  // ElevenLabs Voices
  {
    id: 'rachel',
    name: 'Rachel',
    provider: 'elevenlabs',
    language: 'en-US',
    gender: 'female',
    characteristics: ['Natural', 'Expressive', 'Versatile'],
    previewText: 'Hello, I\'m Rachel. How can I assist you today?',
  },
  {
    id: 'adam',
    name: 'Adam',
    provider: 'elevenlabs',
    language: 'en-US',
    gender: 'male',
    characteristics: ['Deep', 'Authoritative', 'Professional'],
    previewText: 'Hello, I\'m Adam. Welcome to our service.',
  },
];

const VoiceCard: React.FC<{
  voice: Voice;
  isSelected: boolean;
  onSelect: () => void;
  onPreview: () => void;
  isPreviewLoading: boolean;
}> = ({ voice, isSelected, onSelect, onPreview, isPreviewLoading }) => {
  return (
    <div
      onClick={onSelect}
      className={`relative cursor-pointer rounded-lg border-2 p-4 transition-all hover:shadow-md ${
        isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
      }`}
    >
      {/* Selected indicator */}
      {isSelected && (
        <div className="absolute top-2 right-2">
          <div className="bg-blue-500 rounded-full p-1">
            <Check className="w-3 h-3 text-white" />
          </div>
        </div>
      )}

      {/* Voice icon */}
      <div className={`inline-flex p-2 rounded-full mb-3 ${
        voice.gender === 'female'
          ? 'bg-pink-100 dark:bg-pink-900/30'
          : 'bg-blue-100 dark:bg-blue-900/30'
      }`}>
        <Mic className={`w-5 h-5 ${
          voice.gender === 'female'
            ? 'text-pink-600 dark:text-pink-400'
            : 'text-blue-600 dark:text-blue-400'
        }`} />
      </div>

      {/* Voice info */}
      <div className="space-y-2">
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{voice.name}</h4>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {voice.provider === 'sarvam' ? 'Sarvam AI' : 'ElevenLabs'} • {voice.language}
          </p>
        </div>

        {/* Characteristics */}
        <div className="flex flex-wrap gap-1">
          {voice.characteristics.map((char) => (
            <span
              key={char}
              className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full"
            >
              {char}
            </span>
          ))}
        </div>

        {/* Preview button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPreview();
          }}
          disabled={isPreviewLoading}
          className="w-full mt-3 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md text-xs font-medium transition-colors flex items-center justify-center space-x-1 disabled:opacity-50"
        >
          {isPreviewLoading ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Play className="w-3 h-3" />
          )}
          <span>{isPreviewLoading ? 'Playing...' : 'Preview'}</span>
        </button>
      </div>
    </div>
  );
};

export const VoiceSettings: React.FC<VoiceSettingsProps> = ({
  value,
  onChange,
  onPreview,
  className = '',
}) => {
  const [config, setConfig] = useState<VoiceConfig>(value);
  const [provider, setProvider] = useState<TTSProvider>(value.selectedVoice.provider);
  const [customPreviewText, setCustomPreviewText] = useState('');
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);
  const [isCustomPreviewLoading, setIsCustomPreviewLoading] = useState(false);

  const filteredVoices = VOICE_CATALOG.filter((v) => v.provider === provider);

  const updateConfig = (updates: Partial<VoiceConfig>) => {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    onChange(newConfig);
  };

  const updateTuning = (tuning: Partial<VoiceTuning>) => {
    const newTuning = { ...config.tuning, ...tuning };
    updateConfig({ tuning: newTuning });
  };

  const handleVoiceSelect = (voice: Voice) => {
    updateConfig({ selectedVoice: voice });
    setProvider(voice.provider);
  };

  const handleStandardPreview = async (voice: Voice) => {
    if (!onPreview) return;
    setPreviewingVoiceId(voice.id);
    try {
      await onPreview(voice, voice.previewText, config.tuning);
    } finally {
      setPreviewingVoiceId(null);
    }
  };

  const handleCustomPreview = async () => {
    if (!onPreview || !customPreviewText) return;
    setIsCustomPreviewLoading(true);
    try {
      await onPreview(config.selectedVoice, customPreviewText, config.tuning);
    } finally {
      setIsCustomPreviewLoading(false);
    }
  };

  const isSarvamVoice = config.selectedVoice.provider === 'sarvam';

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Voice Settings</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Choose a voice and customize its characteristics
        </p>
      </div>

      {/* Provider Selector */}
      <div className="flex space-x-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        <button
          onClick={() => setProvider('sarvam')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            provider === 'sarvam'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          Sarvam AI
        </button>
        <button
          onClick={() => setProvider('elevenlabs')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            provider === 'elevenlabs'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          ElevenLabs
        </button>
      </div>

      {/* Voice Gallery */}
      <div className="grid grid-cols-2 gap-4">
        {filteredVoices.map((voice) => (
          <VoiceCard
            key={voice.id}
            voice={voice}
            isSelected={config.selectedVoice.id === voice.id}
            onSelect={() => handleVoiceSelect(voice)}
            onPreview={() => handleStandardPreview(voice)}
            isPreviewLoading={previewingVoiceId === voice.id}
          />
        ))}
      </div>

      {/* Custom Preview */}
      <div className="space-y-3 border-t border-gray-200 dark:border-gray-700 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Custom Preview</h4>
        <div className="flex space-x-2">
          <input
            type="text"
            value={customPreviewText}
            onChange={(e) => setCustomPreviewText(e.target.value)}
            placeholder="Enter custom text to preview..."
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={handleCustomPreview}
            disabled={!customPreviewText || isCustomPreviewLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isCustomPreviewLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>Play</span>
          </button>
        </div>
      </div>

      {/* Voice Tuning (Sarvam only) */}
      {isSarvamVoice && (
        <div className="space-y-4 border-t border-gray-200 dark:border-gray-700 pt-6">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Voice Tuning</h4>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Fine-tune the voice characteristics (Sarvam AI only)
          </p>

          {/* Pitch */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 dark:text-gray-300">Pitch</label>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {config.tuning.pitch?.toFixed(2) ?? '0.00'}
              </span>
            </div>
            <input
              type="range"
              min="-0.75"
              max="0.75"
              step="0.05"
              value={config.tuning.pitch ?? 0}
              onChange={(e) => updateTuning({ pitch: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Lower</span>
              <span>Normal</span>
              <span>Higher</span>
            </div>
          </div>

          {/* Speed */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 dark:text-gray-300">Speed</label>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {config.tuning.speed?.toFixed(1) ?? '1.0'}x
              </span>
            </div>
            <input
              type="range"
              min="0.3"
              max="3.0"
              step="0.1"
              value={config.tuning.speed ?? 1.0}
              onChange={(e) => updateTuning({ speed: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>0.3x (Slow)</span>
              <span>1.0x (Normal)</span>
              <span>3.0x (Fast)</span>
            </div>
          </div>

          {/* Volume */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-700 dark:text-gray-300 flex items-center space-x-2">
                <Volume2 className="w-4 h-4" />
                <span>Volume</span>
              </label>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {config.tuning.volume?.toFixed(1) ?? '1.0'}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="3.0"
              step="0.1"
              value={config.tuning.volume ?? 1.0}
              onChange={(e) => updateTuning({ volume: parseFloat(e.target.value) })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Silent</span>
              <span>Normal</span>
              <span>Loud</span>
            </div>
          </div>

          {/* Reset Tuning */}
          <button
            onClick={() => updateConfig({ tuning: {} })}
            className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
          >
            Reset to Default Values
          </button>
        </div>
      )}
    </div>
  );
};

export default VoiceSettings;
