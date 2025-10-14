import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';
import { AudioRecorder } from '../AudioRecorder';

type MediaRecorderListener<T = unknown> = (event: T) => void;
type ListenerMap = Record<string, Array<MediaRecorderListener>>;

function createMediaRecorderMock(resultBuffers: ArrayBuffer[]) {
  const listeners: ListenerMap = {};
  const addEventListener = vi.fn(
    (
      event: string,
      handler: MediaRecorderListener<Event | { data: { size: number; arrayBuffer: () => Promise<ArrayBuffer> } }>,
    ) => {
      (listeners[event] = listeners[event] ?? []).push(handler as MediaRecorderListener);
    },
  );

  const emit = (eventName: string, payload: unknown) => {
    listeners[eventName]?.forEach(handler => handler(payload));
  };

  const mediaRecorderMock: Pick<MediaRecorder, 'addEventListener' | 'start' | 'stop'> = {
    addEventListener,
    start: vi.fn().mockImplementation(() => {
      emit('start', new Event('start'));
      resultBuffers.forEach(buffer => {
        emit('dataavailable', {
          data: {
            size: buffer.byteLength,
            arrayBuffer: vi.fn().mockResolvedValue(buffer),
          },
        });
      });
    }),
    stop: vi.fn().mockImplementation(() => {
      emit('stop', new Event('stop'));
    }),
  };

  return { mediaRecorderMock, emit };
}

describe('AudioRecorder', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn(),
      },
    } as unknown as Navigator);

    vi.stubGlobal('MediaRecorder', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('initializes media stream when start is called', async () => {
    const buffer = new ArrayBuffer(8);
    const { mediaRecorderMock } = createMediaRecorderMock([buffer]);

    const trackMock = { stop: vi.fn() };
    const mediaStreamMock = { getTracks: vi.fn().mockReturnValue([trackMock]) };

    (navigator.mediaDevices.getUserMedia as unknown as Mock).mockResolvedValue(mediaStreamMock as unknown as MediaStream);
    (globalThis.MediaRecorder as unknown as Mock).mockImplementation(() => mediaRecorderMock as unknown as MediaRecorder);

    const recorder = new AudioRecorder();
    await recorder.start();

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true, video: false });
    expect(mediaRecorderMock.start).toHaveBeenCalled();
    await recorder.stop();
    expect(trackMock.stop).toHaveBeenCalled();
  });

  it('invokes onChunk callback for streaming updates', async () => {
    const buffer = new ArrayBuffer(16);
    const { mediaRecorderMock } = createMediaRecorderMock([buffer]);

    const mediaStreamMock = { getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }]) };

    (navigator.mediaDevices.getUserMedia as unknown as Mock).mockResolvedValue(mediaStreamMock as unknown as MediaStream);
    (globalThis.MediaRecorder as unknown as Mock).mockImplementation(() => mediaRecorderMock as unknown as MediaRecorder);

    const onChunk = vi.fn();
    const recorder = new AudioRecorder();
    await recorder.start(onChunk);

    expect(onChunk).toHaveBeenCalledTimes(1);
    const chunk = onChunk.mock.calls[0][0];
    expect(chunk.data).toBeInstanceOf(ArrayBuffer);
    expect(typeof chunk.timestamp).toBe('number');

    const recorded = await recorder.stop();
    expect(recorded).toHaveLength(1);
  });
});
