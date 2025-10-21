import axios from 'axios';

import { appConfig } from './config';

export type TelephonyTrunk = {
  trunk_id: string;
  name: string;
  direction: 'inbound' | 'outbound';
  sip_uri: string;
  transport: string;
};

export async function fetchTelephonyTrunks(): Promise<TelephonyTrunk[]> {
  const response = await axios.get(`${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/trunks`, {
    headers: { 'X-API-Key': appConfig.apiKey },
  });
  return response.data.trunks as TelephonyTrunk[];
}

export async function registerTelephonyTrunk(payload: {
  provider: string;
  trunk_id: string;
  direction: 'inbound' | 'outbound';
  sip_uri: string;
  transport?: string;
  metadata?: Record<string, unknown>;
  credentials?: Record<string, string>;
}) {
  await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/trunks`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
}

export async function initiateOutboundCall(payload: {
  trunk_id: string;
  call_to: string;
  participant_identity?: string;
  room_name: string;
  wait_until_answered?: boolean;
}) {
  await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/calls`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
}

// Voice Discovery API

export type TTSProvider = {
  id: string;
  name: string;
  description: string;
  supports_tuning: boolean;
  languages: string[];
};

export type Voice = {
  provider: string;
  voice_id: string;
  display_name: string;
  gender?: 'male' | 'female' | 'neutral';
  languages: string[];
  characteristics?: string[];
};

export type VoiceTuning = {
  pitch?: number;
  pace?: number;
  loudness?: number;
};

export async function fetchTTSProviders(): Promise<TTSProvider[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/tts/providers`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data.providers;
}

export async function fetchVoices(params?: {
  provider?: string;
  language?: string;
  include_custom?: boolean;
}): Promise<Voice[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/tts/voices`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
      params,
    },
  );
  return response.data.voices;
}

export async function fetchCustomElevenLabsVoices(apiKey?: string): Promise<Voice[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/tts/voices/elevenlabs/custom`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
      params: apiKey ? { api_key: apiKey } : undefined,
    },
  );
  return response.data.voices;
}

export async function previewVoice(payload: {
  voice_id: string;
  provider: string;
  text?: string;
  language_code?: string;
  pitch?: number;
  pace?: number;
  loudness?: number;
}): Promise<{ audio_b64: string; mime_type: string }> {
  const response = await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/tts/voices/preview`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data;
}

// LLM Provider API

export type LLMProvider = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  requires_api_key: boolean;
  supports_streaming: boolean;
  model_count: number;
};

export type LLMModel = {
  id: string;
  name: string;
  provider: string;
  context_window: number;
  max_output_tokens: number;
  supports_streaming: boolean;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
  description?: string;
};

export async function fetchLLMProviders(): Promise<LLMProvider[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/llm/providers`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data.providers;
}

export async function fetchLLMModels(provider?: string): Promise<LLMModel[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/llm/models`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
      params: provider ? { provider } : undefined,
    },
  );
  return response.data.models;
}

// System Prompt API

export type SystemPrompt = {
  id: string;
  name: string;
  prompt_text: string;
  category: string;
  is_default: boolean;
  is_template: boolean;
  variables: string[];
  meta_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export async function fetchSystemPrompts(params?: {
  category?: string;
  is_template?: boolean;
}): Promise<SystemPrompt[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
      params,
    },
  );
  return response.data.prompts;
}

export async function fetchPromptTemplates(): Promise<SystemPrompt[]> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts/templates`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data.templates;
}

export async function fetchSystemPrompt(id: string): Promise<SystemPrompt> {
  const response = await axios.get(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts/${id}`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data;
}

export async function createSystemPrompt(payload: {
  name: string;
  prompt_text: string;
  category: string;
  is_default?: boolean;
  variables?: string[];
  meta_data?: Record<string, unknown>;
}): Promise<SystemPrompt> {
  const response = await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data;
}

export async function updateSystemPrompt(
  id: string,
  payload: {
    name?: string;
    prompt_text?: string;
    category?: string;
    is_default?: boolean;
    variables?: string[];
    meta_data?: Record<string, unknown>;
  },
): Promise<SystemPrompt> {
  const response = await axios.put(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts/${id}`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
  return response.data;
}

export async function deleteSystemPrompt(id: string): Promise<void> {
  await axios.delete(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/system-prompts/${id}`,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
}

