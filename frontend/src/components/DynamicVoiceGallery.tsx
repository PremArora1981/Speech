import React, { useEffect, useState } from 'react';
import { Play, Volume2, RefreshCw, Loader2, Search } from 'lucide-react';
import { fetchVoices, fetchCustomElevenLabsVoices, previewVoice } from '../lib/api';
import type { Voice, VoiceTuning } from '../lib/api';

export type VoiceConfig = {
  provider: string;
  voice_id: string;
  display_name: string;
  tuning: VoiceTuning;
};

type DynamicVoiceGalleryProps = {
  value: VoiceConfig;
  onChange: (config: VoiceConfig) => void;
  provider?: string;
  language?: string;
};

export const DynamicVoiceGallery: React.FC<DynamicVoiceGalleryProps> = ({
  value,
  onChange,
  provider,
  language,
}) => {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [customVoices, setCustomVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [genderFilter, setGenderFilter] = useState<string>('');
  const [showCustom, setShowCustom] = useState(true);
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);
  const [customPreviewText, setCustomPreviewText] = useState('');
  const [showCustomPreview, setShowCustomPreview] = useState(false);

  // Tuning state (Sarvam only)
  const [tuning, setTuning] = useState<VoiceTuning>(value.tuning || {});

  useEffect(() => {
    loadVoices();
  }, [provider, language]);

  const loadVoices = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch standard voices
      const voicesData = await fetchVoices({
        provider,
        language,
        include_custom: false,
      });
      setVoices(voicesData);

      // Fetch custom ElevenLabs voices if ElevenLabs provider
      if (!provider || provider === 'elevenlabs') {
        try {
          const customData = await fetchCustomElevenLabsVoices();
          setCustomVoices(customData);
        } catch (err) {
          // Custom voices are optional, don't fail if not available
          console.warn('Custom voices not available:', err);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load voices');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadVoices();
    setRefreshing(false);
  };

  const handleVoiceSelect = (voice: Voice) => {
    onChange({
      provider: voice.provider,
      voice_id: voice.voice_id,
      display_name: voice.display_name,
      tuning,
    });
  };

  const handlePreview = async (voice: Voice, customText?: string) => {
    try {
      setPreviewingVoice(voice.voice_id);
      const result = await previewVoice({
        voice_id: voice.voice_id,
        provider: voice.provider,
        text: customText || `Hello, this is ${voice.display_name}. How can I help you today?`,
        language_code: voice.languages[0] || 'en-IN',
        ...tuning,
      });

      // Play the audio
      const audio = new Audio(`data:${result.mime_type};base64,${result.audio_b64}`);
      await audio.play();
    } catch (err: any) {
      console.error('Preview failed:', err);
      alert(err.response?.data?.detail || 'Failed to preview voice');
    } finally {
      setPreviewingVoice(null);
    }
  };

  const handleTuningChange = (key: keyof VoiceTuning, value: number) => {
    const newTuning = { ...tuning, [key]: value };
    setTuning(newTuning);
    // Update config immediately
    onChange({
      ...value,
      tuning: newTuning,
    });
  };

  // Filter voices
  const filteredVoices = voices.filter((voice) => {
    if (searchQuery && !voice.display_name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (genderFilter && voice.gender !== genderFilter) {
      return false;
    }
    return true;
  });

  const filteredCustomVoices = customVoices.filter((voice) => {
    if (searchQuery && !voice.display_name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Voice Selection</h3>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search voices..."
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={genderFilter}
          onChange={(e) => setGenderFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Genders</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="neutral">Neutral</option>
        </select>
      </div>

      {/* Custom Voices Section */}
      {customVoices.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-medium text-gray-900 flex items-center gap-2">
              My Custom Voices
              <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                {customVoices.length}
              </span>
            </h4>
            <button
              onClick={() => setShowCustom(!showCustom)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showCustom ? 'Hide' : 'Show'}
            </button>
          </div>

          {showCustom && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
              {filteredCustomVoices.map((voice) => (
                <VoiceCard
                  key={voice.voice_id}
                  voice={voice}
                  isSelected={value.voice_id === voice.voice_id}
                  onSelect={() => handleVoiceSelect(voice)}
                  onPreview={() => handlePreview(voice)}
                  isPreviewing={previewingVoice === voice.voice_id}
                  isCustom
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Standard Voices */}
      <div className="mb-4">
        <h4 className="font-medium text-gray-900 mb-3">
          Available Voices ({filteredVoices.length})
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredVoices.map((voice) => (
            <VoiceCard
              key={voice.voice_id}
              voice={voice}
              isSelected={value.voice_id === voice.voice_id}
              onSelect={() => handleVoiceSelect(voice)}
              onPreview={() => handlePreview(voice)}
              isPreviewing={previewingVoice === voice.voice_id}
            />
          ))}
        </div>
      </div>

      {/* Voice Tuning (Sarvam only) */}
      {value.provider === 'sarvam' && (
        <div className="mt-6 p-4 bg-gray-50 rounded-md">
          <h4 className="font-medium text-gray-900 mb-3">Voice Tuning</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pitch: {tuning.pitch?.toFixed(2) || 0}
              </label>
              <input
                type="range"
                min="-0.75"
                max="0.75"
                step="0.05"
                value={tuning.pitch || 0}
                onChange={(e) => handleTuningChange('pitch', parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Lower</span>
                <span>Higher</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Speed: {tuning.pace?.toFixed(2) || 1.0}
              </label>
              <input
                type="range"
                min="0.3"
                max="3.0"
                step="0.1"
                value={tuning.pace || 1.0}
                onChange={(e) => handleTuningChange('pace', parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Slower</span>
                <span>Faster</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Volume: {tuning.loudness?.toFixed(2) || 1.0}
              </label>
              <input
                type="range"
                min="0"
                max="3.0"
                step="0.1"
                value={tuning.loudness || 1.0}
                onChange={(e) => handleTuningChange('loudness', parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Quieter</span>
                <span>Louder</span>
              </div>
            </div>

            <button
              onClick={() => {
                setTuning({});
                onChange({ ...value, tuning: {} });
              }}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Reset to Default
            </button>
          </div>
        </div>
      )}

      {/* Custom Preview */}
      <div className="mt-4 p-4 border border-gray-200 rounded-md">
        <button
          onClick={() => setShowCustomPreview(!showCustomPreview)}
          className="text-sm font-medium text-gray-900 mb-2"
        >
          {showCustomPreview ? '▼' : '▶'} Custom Text Preview
        </button>
        {showCustomPreview && (
          <div className="mt-2">
            <input
              type="text"
              value={customPreviewText}
              onChange={(e) => setCustomPreviewText(e.target.value)}
              placeholder="Enter text to preview..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
            />
            <button
              onClick={() => {
                const selectedVoice = [...voices, ...customVoices].find(
                  (v) => v.voice_id === value.voice_id
                );
                if (selectedVoice && customPreviewText) {
                  handlePreview(selectedVoice, customPreviewText);
                }
              }}
              disabled={!value.voice_id || !customPreviewText || previewingVoice !== null}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
            >
              {previewingVoice ? 'Playing...' : 'Preview Custom Text'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Voice Card Component
const VoiceCard: React.FC<{
  voice: Voice;
  isSelected: boolean;
  onSelect: () => void;
  onPreview: () => void;
  isPreviewing: boolean;
  isCustom?: boolean;
}> = ({ voice, isSelected, onSelect, onPreview, isPreviewing, isCustom }) => {
  return (
    <div
      onClick={onSelect}
      className={`p-4 border rounded-lg cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
          : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h5 className="font-medium text-gray-900">{voice.display_name}</h5>
          <div className="flex gap-2 mt-1">
            {voice.gender && (
              <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                {voice.gender}
              </span>
            )}
            {isCustom && (
              <span className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded">
                Custom
              </span>
            )}
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPreview();
          }}
          disabled={isPreviewing}
          className="p-2 hover:bg-white rounded-full transition-colors disabled:opacity-50"
        >
          {isPreviewing ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          ) : (
            <Play className="w-4 h-4 text-blue-600" />
          )}
        </button>
      </div>

      {voice.languages && voice.languages.length > 0 && (
        <div className="text-xs text-gray-500 mb-2">
          {voice.languages.slice(0, 2).join(', ')}
          {voice.languages.length > 2 && ` +${voice.languages.length - 2}`}
        </div>
      )}

      {voice.characteristics && voice.characteristics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {voice.characteristics.slice(0, 3).map((char) => (
            <span key={char} className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded">
              {char}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
