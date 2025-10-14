export type AudioPlaybackState = 'idle' | 'queued' | 'playing' | 'error';

type QueueItem = {
  buffer: ArrayBuffer;
  contentType?: string;
};

type AudioPlayerCallbacks = {
  onStateChange?: (state: AudioPlaybackState) => void;
  onError?: (error: Error) => void;
};

type AudioContextFactory = () => AudioContext;

export const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
  const binaryString = atob(base64);
  const length = binaryString.length;
  const bytes = new Uint8Array(length);
  for (let index = 0; index < length; index += 1) {
    bytes[index] = binaryString.charCodeAt(index);
  }
  return bytes.buffer;
};

const getDefaultAudioContextFactory = (): AudioContextFactory => {
  const Ctor = (window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext);
  if (!Ctor) {
    throw new Error('AudioContext is not supported in this environment.');
  }
  return () => new Ctor();
};

export class AudioPlayer {
  private readonly callbacks: AudioPlayerCallbacks;

  private readonly createContext: AudioContextFactory;

  private context: AudioContext | null = null;

  private queue: QueueItem[] = [];

  private isProcessing = false;

  private currentSource: AudioBufferSourceNode | null = null;

  constructor(callbacks: AudioPlayerCallbacks = {}, factory: AudioContextFactory | null = null) {
    this.callbacks = callbacks;
    this.createContext = factory ?? getDefaultAudioContextFactory();
  }

  enqueue(base64Audio: string, contentType?: string): void {
    try {
      const buffer = base64ToArrayBuffer(base64Audio);
      this.queue.push({ buffer, contentType });
      this.notify(this.currentSource ? 'queued' : 'queued');
      void this.processQueue();
    } catch (error) {
      this.notify('error');
      this.callbacks.onError?.(error as Error);
    }
  }

  stop(): void {
    this.queue = [];
    if (this.currentSource) {
      try {
        this.currentSource.onended = null;
        this.currentSource.stop();
      } catch (error) {
        this.callbacks.onError?.(error as Error);
      }
      this.currentSource.disconnect();
      this.currentSource = null;
    }
    this.notify('idle');
  }

  async dispose(): Promise<void> {
    this.stop();
    if (this.context) {
      await this.context.close().catch(() => undefined);
      this.context = null;
    }
  }

  private async processQueue(): Promise<void> {
    if (this.isProcessing) {
      return;
    }
    this.isProcessing = true;

    while (this.queue.length > 0) {
      const { buffer } = this.queue.shift()!;
      try {
        const context = this.ensureContext();
        if (context.state === 'suspended') {
          await context.resume();
        }

        const audioBuffer = await context.decodeAudioData(buffer.slice(0));
        const source = context.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(context.destination);
        this.currentSource = source;
        this.notify('playing');

        await new Promise<void>((resolve, reject) => {
          source.onended = () => resolve();
          try {
            source.start(0);
          } catch (error) {
            reject(error);
          }
        });

        source.disconnect();
        this.currentSource = null;
        if (this.queue.length === 0) {
          this.notify('idle');
        } else {
          this.notify('queued');
        }
      } catch (error) {
        this.callbacks.onError?.(error as Error);
        this.notify('error');
      }
    }

    this.isProcessing = false;
  }

  private ensureContext(): AudioContext {
    if (!this.context) {
      this.context = this.createContext();
    }
    return this.context;
  }

  private notify(state: AudioPlaybackState): void {
    this.callbacks.onStateChange?.(state);
  }
}

