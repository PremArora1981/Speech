export type AudioChunk = {
  data: ArrayBuffer;
  timestamp: number;
};

export interface AudioProcessingOptions {
  noiseSuppression?: boolean;
  echoCancellation?: boolean;
  autoGainControl?: boolean;
  vadEnabled?: boolean;
  vadSensitivity?: number; // 0-1 scale
}

export interface VoiceActivityEvent {
  isSpeaking: boolean;
  timestamp: number;
  confidence: number;
}

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: AudioChunk[] = [];
  private onChunkCallback: ((chunk: AudioChunk) => void) | null = null;
  private onVoiceActivityCallback: ((event: VoiceActivityEvent) => void) | null = null;

  // VAD state
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private vadIntervalId: number | null = null;
  private vadSensitivity: number = 0.7;
  private isSpeaking: boolean = false;

  async start(
    onChunk?: (chunk: AudioChunk) => void,
    options?: AudioProcessingOptions,
    onVoiceActivity?: (event: VoiceActivityEvent) => void
  ): Promise<void> {
    const constraints: MediaStreamConstraints = {
      audio: {
        noiseSuppression: options?.noiseSuppression ?? true,
        echoCancellation: options?.echoCancellation ?? true,
        autoGainControl: options?.autoGainControl ?? true,
      },
      video: false,
    };

    this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: 'audio/webm' });

    this.onChunkCallback = onChunk ?? null;
    this.onVoiceActivityCallback = onVoiceActivity ?? null;
    this.chunks = [];

    this.mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data && event.data.size > 0) {
        event.data.arrayBuffer().then((buffer) => {
          const chunk: AudioChunk = { data: buffer, timestamp: Date.now() };
          this.chunks.push(chunk);
          this.onChunkCallback?.(chunk);
        });
      }
    });

    this.mediaRecorder.start(200); // collect chunks every 200ms

    // Initialize VAD if enabled
    if (options?.vadEnabled) {
      this.vadSensitivity = options.vadSensitivity ?? 0.7;
      await this.initializeVAD();
    }
  }

  private async initializeVAD(): Promise<void> {
    if (!this.mediaStream) return;

    this.audioContext = new AudioContext();
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 2048;
    source.connect(this.analyser);

    // Start VAD monitoring
    this.vadIntervalId = window.setInterval(() => {
      this.detectVoiceActivity();
    }, 100); // Check every 100ms
  }

  private detectVoiceActivity(): void {
    if (!this.analyser || !this.onVoiceActivityCallback) return;

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    this.analyser.getByteFrequencyData(dataArray);

    // Calculate average volume
    const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;

    // Dynamic threshold based on sensitivity
    // Sensitivity 0 = 40 threshold, Sensitivity 1 = 15 threshold
    const baseThreshold = 40 - (this.vadSensitivity * 25);

    // Check if speech is detected
    const wasSpeaking = this.isSpeaking;
    this.isSpeaking = average > baseThreshold;

    // Only emit event on state change
    if (this.isSpeaking !== wasSpeaking) {
      this.onVoiceActivityCallback({
        isSpeaking: this.isSpeaking,
        timestamp: Date.now(),
        confidence: Math.min(average / 100, 1.0), // Normalize to 0-1
      });
    }
  }

  getIsSpeaking(): boolean {
    return this.isSpeaking;
  }

  setVadSensitivity(sensitivity: number): void {
    this.vadSensitivity = Math.max(0, Math.min(1, sensitivity));
  }

  async stop(): Promise<AudioChunk[]> {
    if (!this.mediaRecorder) return [];

    const completed = new Promise<void>((resolve) => {
      this.mediaRecorder?.addEventListener('stop', () => resolve(), { once: true });
    });

    this.mediaRecorder.stop();
    await completed;

    // Clean up VAD
    if (this.vadIntervalId !== null) {
      clearInterval(this.vadIntervalId);
      this.vadIntervalId = null;
    }
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
    this.analyser = null;
    this.isSpeaking = false;

    this.mediaStream?.getTracks().forEach((track) => track.stop());
    const recordedChunks = this.chunks;
    this.chunks = [];
    this.onChunkCallback = null;
    this.onVoiceActivityCallback = null;
    this.mediaRecorder = null;
    this.mediaStream = null;
    return recordedChunks;
  }
}
