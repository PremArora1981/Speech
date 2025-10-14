export const appConfig = {
  apiKey: import.meta.env.VITE_API_KEY ?? '',
  restTtsUrl: import.meta.env.VITE_TTS_URL ?? 'http://localhost:8000/api/v1/tts',
  voiceSessionWsUrl: import.meta.env.VITE_VOICE_WS_URL ?? 'ws://localhost:8000/api/v1/voice-session',
};
