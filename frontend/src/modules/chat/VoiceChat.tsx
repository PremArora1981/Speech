import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Mic, AlertTriangle, Send, Loader2 } from 'lucide-react';
import axios from 'axios';
import { AudioRecorder, type AudioChunk } from '../../services/audio/AudioRecorder';
import { AudioPlayer, type AudioPlaybackState } from '../../services/audio/AudioPlayer';

const WEB_SOCKET_URL = import.meta.env.VITE_VOICE_WS_URL ?? 'ws://localhost:8000/api/v1/voice-session';
const REST_TTS_URL = import.meta.env.VITE_TTS_URL ?? 'http://localhost:8000/api/v1/tts';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

type VoiceChatProps = {
  sessionId: string;
  onSessionChange: (id: string) => void;
  optimizationLevel: 'quality' | 'balanced_quality' | 'balanced' | 'balanced_speed' | 'speed';
};

type MessageStatus = 'streaming' | 'final';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: string;
  status: MessageStatus;
};

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type RecordingStatus = 'idle' | 'recording';

type OutgoingMessage =
  | { type: 'start'; sessionId: string; optimizationLevel: VoiceChatProps['optimizationLevel'] }
  | { type: 'audio'; sessionId: string; audio: string; timestamp: number; optimizationLevel: VoiceChatProps['optimizationLevel'] }
  | { type: 'stop'; sessionId: string; optimizationLevel: VoiceChatProps['optimizationLevel'] };

type IncomingMessage =
  | { type: 'message'; text: string }
  | { type: 'transcript'; text: string; final?: boolean }
  | { type: 'audio'; audio_b64: string; contentType?: string }
  | { type: 'session'; sessionId: string }
  | { type: 'error'; message: string };

const encodeChunk = (chunk: AudioChunk): string =>
  btoa(String.fromCharCode(...new Uint8Array(chunk.data)));

export function VoiceChat({ sessionId, onSessionChange, optimizationLevel }: VoiceChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [recordingStatus, setRecordingStatus] = useState<RecordingStatus>('idle');
  const [audioStatus, setAudioStatus] = useState<AudioPlaybackState>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<AudioRecorder | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const pendingSessionId = useRef<string>(sessionId);
  const reconnectTimerRef = useRef<number | null>(null);
  const transcriptMessageIdRef = useRef<string | null>(null);
  const audioStatusMessageIdRef = useRef<string | null>(null);
  const pendingMessagesRef = useRef<OutgoingMessage[]>([]);

  const stableSessionId = useMemo(() => {
    if (sessionId && sessionId !== pendingSessionId.current) {
      pendingSessionId.current = sessionId;
      return sessionId;
    }

    if (!pendingSessionId.current) {
      pendingSessionId.current = crypto.randomUUID();
      onSessionChange(pendingSessionId.current);
    }
    return pendingSessionId.current;
  }, [sessionId, onSessionChange]);

  const ensureRecorder = useCallback(() => {
    if (!recorderRef.current) {
      recorderRef.current = new AudioRecorder();
    }
    return recorderRef.current;
  }, []);

  const updateAudioStatusMessage = useCallback((text: string, status: MessageStatus) => {
    setMessages(prev => {
      const messageId = audioStatusMessageIdRef.current ?? crypto.randomUUID();
      const next = [...prev];
      const index = next.findIndex(message => message.id === messageId);
      const payload: Message = {
        id: messageId,
        role: 'assistant',
        text,
        timestamp: new Date().toISOString(),
        status,
      };

      if (index >= 0) {
        next[index] = payload;
      } else {
        next.push(payload);
      }

      audioStatusMessageIdRef.current = status === 'final' ? null : messageId;
      return next;
    });
  }, []);

  const ensureAudioPlayer = useCallback(() => {
    if (!audioPlayerRef.current) {
      audioPlayerRef.current = new AudioPlayer({
        onStateChange: state => {
          setAudioStatus(state);
          if (state === 'playing') {
            updateAudioStatusMessage('[Playing audio response]', 'streaming');
          } else if (state === 'queued') {
            updateAudioStatusMessage('[Audio response queued]', 'streaming');
          } else if (state === 'idle') {
            if (audioStatusMessageIdRef.current) {
              updateAudioStatusMessage('[Audio playback complete]', 'final');
            }
          } else if (state === 'error') {
            updateAudioStatusMessage('[Audio playback error]', 'final');
          }
        },
        onError: error => {
          console.error(error);
          setError('Audio playback failed.');
          setAudioStatus('error');
          updateAudioStatusMessage('[Audio playback error]', 'final');
        },
      });
    }
    return audioPlayerRef.current;
  }, [setError, updateAudioStatusMessage]);

  const flushPendingMessages = useCallback(() => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    const next = pendingMessagesRef.current.splice(0);
    next.forEach(message => {
      socket.send(JSON.stringify(message));
    });
  }, []);

  const sendWsMessage = useCallback(
    (payload: OutgoingMessage) => {
      const socket = wsRef.current;
      if (!socket) {
        if (payload.type !== 'audio') {
          pendingMessagesRef.current.push(payload);
        }
        setError('Voice connection is not ready.');
        return false;
      }

      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload));
        return true;
      }

      if (socket.readyState === WebSocket.CONNECTING && payload.type !== 'audio') {
        pendingMessagesRef.current.push(payload);
        return true;
      }

      setError('Voice connection is not ready.');
      return false;
    },
    [],
  );

  const updateTranscriptMessage = useCallback((text: string, isFinal: boolean, role: Message['role']) => {
    setMessages(prev => {
      const messageId = transcriptMessageIdRef.current ?? crypto.randomUUID();
      const next = [...prev];
      const idx = next.findIndex(item => item.id === messageId);
      const payload: Message = {
        id: messageId,
        role,
        text,
        timestamp: new Date().toISOString(),
        status: isFinal ? 'final' : 'streaming',
      };
      if (idx >= 0) {
        next[idx] = payload;
      } else {
        next.push(payload);
      }
      transcriptMessageIdRef.current = isFinal ? null : messageId;
      return next;
    });
  }, []);

  const teardownSocket = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }
    setAudioStatus('idle');
    if (audioStatusMessageIdRef.current) {
      updateAudioStatusMessage('[Audio playback stopped]', 'final');
    }
    pendingMessagesRef.current.length = 0;
  }, [updateAudioStatusMessage]);

  const handleSocketMessage = useCallback(
    (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as IncomingMessage;
      if (data.type === 'session') {
        pendingSessionId.current = data.sessionId;
        onSessionChange(data.sessionId);
        return;
      }

      if (data.type === 'message') {
        setMessages(prev => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            text: data.text,
            timestamp: new Date().toISOString(),
            status: 'final',
          },
        ]);
      }

      if (data.type === 'transcript') {
        updateTranscriptMessage(data.text, Boolean(data.final), 'assistant');
      }

      if (data.type === 'audio') {
        try {
          const player = ensureAudioPlayer();
          player.enqueue(data.audio_b64, data.contentType);
          updateAudioStatusMessage('[Audio response received]', 'streaming');
        } catch (err) {
          console.error(err);
          updateAudioStatusMessage('[Audio response failed to enqueue]', 'final');
        }
      }

      if (data.type === 'error') {
        setError(data.message);
        updateAudioStatusMessage(`[Server error] ${data.message}`, 'final');
      }
    },
    [ensureAudioPlayer, onSessionChange, updateAudioStatusMessage, updateTranscriptMessage],
  );

  const connectWebSocket = useCallback(() => {
    const current = wsRef.current;
    if (current && current.readyState === WebSocket.OPEN) {
      return;
    }

    if (current && current.readyState === WebSocket.CONNECTING) {
      return;
    }

    teardownSocket();
    setConnectionStatus('connecting');

    const socket = new WebSocket(WEB_SOCKET_URL);
    wsRef.current = socket;

    socket.addEventListener('open', () => {
      setConnectionStatus('connected');
      socket.send(JSON.stringify({ type: 'auth', apiKey: API_KEY, sessionId: stableSessionId }));
      flushPendingMessages();
      setError(null);
    });

    socket.addEventListener('message', handleSocketMessage);

    socket.addEventListener('close', () => {
      setConnectionStatus('disconnected');
      setRecordingStatus('idle');
      audioPlayerRef.current?.stop();
      setAudioStatus('idle');
      pendingMessagesRef.current.length = 0;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      reconnectTimerRef.current = window.setTimeout(() => {
        connectWebSocket();
      }, 1000);
    });

    socket.addEventListener('error', () => {
      setConnectionStatus('error');
      setError('WebSocket connection error.');
    });
  }, [flushPendingMessages, handleSocketMessage, stableSessionId, teardownSocket]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      teardownSocket();
      void audioPlayerRef.current?.dispose();
    };
  }, [connectWebSocket, teardownSocket]);

  const sendTextMessage = useCallback(async () => {
    if (!input.trim()) return;
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: input,
      timestamp: new Date().toISOString(),
      status: 'final',
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const response = await axios.post(
        REST_TTS_URL,
        {
          text: userMessage.text,
          language_code: 'en-IN',
          voice: { provider: 'sarvam', voice_id: 'anushka' },
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
          },
        },
      );
      const { audio_b64: audioBase64, mime_type: mimeType, metadata } = response.data ?? {};
      if (audioBase64) {
        try {
          const player = ensureAudioPlayer();
          player.enqueue(audioBase64, mimeType ?? metadata?.mime_type);
          updateAudioStatusMessage('[Audio response received]', 'streaming');
        } catch (err) {
          console.error(err);
          setError('Failed to play audio response.');
          updateAudioStatusMessage('[Audio response failed to enqueue]', 'final');
        }
      }
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: metadata?.text ?? metadata?.prompt ?? '[Audio response ready]',
          timestamp: new Date().toISOString(),
          status: 'final',
        },
      ]);
    } catch (err) {
      console.error(err);
      setError('Failed to send message.');
      updateAudioStatusMessage('[TTS request failed]', 'final');
    }
  }, [ensureAudioPlayer, input, updateAudioStatusMessage]);

  const startRecording = useCallback(async () => {
    if (recordingStatus === 'recording') {
      return;
    }

    setError(null);

    const recorder = ensureRecorder();

    const ok = sendWsMessage({ type: 'start', sessionId: stableSessionId, optimizationLevel });
    if (!ok) {
      return;
    }

    transcriptMessageIdRef.current = null;

    try {
      await recorder.start(chunk => {
        sendWsMessage({
          type: 'audio',
          sessionId: stableSessionId,
          audio: encodeChunk(chunk),
          timestamp: chunk.timestamp,
          optimizationLevel,
        });
      });
      setRecordingStatus('recording');
    } catch (err) {
      console.error(err);
      setError('Unable to access microphone.');
      sendWsMessage({ type: 'stop', sessionId: stableSessionId, optimizationLevel });
    }
  }, [ensureRecorder, recordingStatus, sendWsMessage, stableSessionId, optimizationLevel]);

  const stopRecording = useCallback(async () => {
    if (recordingStatus !== 'recording') {
      return;
    }
    const recorder = recorderRef.current;
    if (!recorder) {
      return;
    }

    setRecordingStatus('idle');
    try {
      await recorder.stop();
    } catch (err) {
      console.error(err);
    }
    sendWsMessage({ type: 'stop', sessionId: stableSessionId, optimizationLevel });
  }, [recordingStatus, sendWsMessage, stableSessionId, optimizationLevel]);

  const toggleRecording = useCallback(() => {
    if (recordingStatus === 'recording') {
      void stopRecording();
    } else {
      void startRecording();
    }
  }, [recordingStatus, startRecording, stopRecording]);

  useEffect(() => () => {
    if (recordingStatus === 'recording') {
      void stopRecording();
    }
    void audioPlayerRef.current?.dispose();
    setAudioStatus('idle');
  }, [recordingStatus, stopRecording]);

  useEffect(() => {
    if (!wsRef.current) return;
    const socket = wsRef.current;
    return () => {
      socket.close();
    };
  }, []);

  return (
    <section className='space-y-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-6 shadow-xl'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-xl font-semibold text-neutral-100'>Live Voice Session</h2>
          <p className='text-sm text-neutral-400'>Session ID: {stableSessionId}</p>
        </div>
        <div className='flex items-center gap-2 text-xs font-medium uppercase'>
          <span
            className={
              connectionStatus === 'connected'
                ? 'rounded-full bg-emerald-500/20 px-3 py-1 text-emerald-300'
                : connectionStatus === 'connecting'
                  ? 'flex items-center gap-1 rounded-full bg-neutral-700/30 px-3 py-1 text-neutral-300'
                  : connectionStatus === 'error'
                    ? 'rounded-full bg-red-500/20 px-3 py-1 text-red-200'
                    : 'rounded-full bg-neutral-700/30 px-3 py-1 text-neutral-400'
            }
          >
            {connectionStatus === 'connecting' ? (
              <>
                <Loader2 className='h-3.5 w-3.5 animate-spin' /> connecting
              </>
            ) : (
              connectionStatus
            )}
          </span>
          <span
            className={
              recordingStatus === 'recording'
                ? 'rounded-full bg-red-500/20 px-3 py-1 text-red-300'
                : 'rounded-full bg-neutral-700/30 px-3 py-1 text-neutral-400'
            }
          >
            {recordingStatus === 'recording' ? 'rec' : 'idle'}
          </span>
          <span
            className={
              audioStatus === 'playing'
                ? 'rounded-full bg-sky-500/20 px-3 py-1 text-sky-300'
                : audioStatus === 'queued'
                  ? 'rounded-full bg-amber-500/20 px-3 py-1 text-amber-200'
                  : audioStatus === 'error'
                    ? 'rounded-full bg-red-500/20 px-3 py-1 text-red-200'
                    : 'rounded-full bg-neutral-700/30 px-3 py-1 text-neutral-400'
            }
          >
            {audioStatus}
          </span>
        </div>
      </div>

      <div className='flex flex-col gap-4 rounded-xl border border-neutral-800 bg-neutral-950/50 p-4'>
        <div className='flex max-h-96 flex-col gap-4 overflow-y-auto pr-2'>
          {messages.map(message => (
            <div key={message.id} className='flex flex-col gap-1'>
              <span className='text-xs uppercase text-neutral-500'>{message.role}</span>
              <p
                className={`rounded-lg px-3 py-2 text-sm text-neutral-100 ${
                  message.role === 'assistant' ? 'bg-neutral-800' : 'bg-neutral-800/80'
                } ${message.status === 'streaming' ? 'italic opacity-80' : ''}`}
              >
                {message.text}
              </p>
            </div>
          ))}
          {messages.length === 0 && (
            <div className='rounded-lg border border-dashed border-neutral-700 px-4 py-8 text-center text-neutral-500'>
              No messages yet. Start a conversation below.
            </div>
          )}
        </div>
      </div>

      <div className='flex items-center gap-4'>
        <button
          type='button'
          className={`flex h-12 w-12 items-center justify-center rounded-full text-neutral-900 transition ${
            recordingStatus === 'recording' ? 'bg-red-500 hover:bg-red-400' : 'bg-emerald-500 hover:bg-emerald-400'
          } ${connectionStatus !== 'connected' && recordingStatus !== 'recording' ? 'opacity-50' : ''}`}
          disabled={connectionStatus !== 'connected' && recordingStatus !== 'recording'}
          onClick={toggleRecording}
        >
          <Mic className='h-5 w-5' />
        </button>
        <div className='flex-1'>
          <input
            className='h-12 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-4 text-sm text-neutral-100 placeholder:text-neutral-500 focus:border-emerald-500 focus:outline-none'
            placeholder='Type a message...'
            value={input}
            onChange={event => setInput(event.currentTarget.value)}
            onKeyDown={event => event.key === 'Enter' && sendTextMessage()}
          />
        </div>
        <button
          type='button'
          onClick={sendTextMessage}
          className='flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500 text-neutral-900 transition hover:bg-emerald-400'
        >
          <Send className='h-5 w-5' />
        </button>
      </div>

      {error && (
        <div className='flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200'>
          <AlertTriangle className='mt-0.5 h-4 w-4' />
          <span>{error}</span>
        </div>
      )}
    </section>
  );
}
