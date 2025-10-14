export type AudioChunk = {
  data: ArrayBuffer;
  timestamp: number;
};

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: AudioChunk[] = [];
  private onChunkCallback: ((chunk: AudioChunk) => void) | null = null;

  async start(onChunk?: (chunk: AudioChunk) => void): Promise<void> {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: 'audio/webm' });

    this.onChunkCallback = onChunk ?? null;
    this.chunks = [];
    this.mediaRecorder.addEventListener('dataavailable', event => {
      if (event.data && event.data.size > 0) {
        event.data.arrayBuffer().then(buffer => {
          const chunk: AudioChunk = { data: buffer, timestamp: Date.now() };
          this.chunks.push(chunk);
          this.onChunkCallback?.(chunk);
        });
      }
    });

    this.mediaRecorder.start(200); // collect chunks every 200ms
  }

  async stop(): Promise<AudioChunk[]> {
    if (!this.mediaRecorder) return [];

    const completed = new Promise<void>(resolve => {
      this.mediaRecorder?.addEventListener('stop', () => resolve(), { once: true });
    });

    this.mediaRecorder.stop();
    await completed;

    this.mediaStream?.getTracks().forEach(track => track.stop());
    const recordedChunks = this.chunks;
    this.chunks = [];
    this.onChunkCallback = null;
    this.mediaRecorder = null;
    this.mediaStream = null;
    return recordedChunks;
  }
}
