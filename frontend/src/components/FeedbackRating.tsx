import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';

type FeedbackRatingProps = {
  messageId: string;
  sessionId: string;
  turnId?: string;
  userInput?: string;
  assistantResponse?: string;
  apiUrl?: string;
  apiKey?: string;
  onFeedbackSubmitted?: (rating: number) => void;
};

export function FeedbackRating({
  messageId,
  sessionId,
  turnId,
  userInput,
  assistantResponse,
  apiUrl = 'http://localhost:8000/api/v1',
  apiKey = '',
  onFeedbackSubmitted,
}: FeedbackRatingProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFeedback = async (selectedRating: number) => {
    if (submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({
          session_id: sessionId,
          turn_id: turnId,
          message_id: messageId,
          rating: selectedRating,
          rating_type: 'thumbs',
          user_input: userInput,
          assistant_response: assistantResponse,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to submit feedback: ${response.statusText}`);
      }

      setRating(selectedRating);
      onFeedbackSubmitted?.(selectedRating);
    } catch (err) {
      console.error('Feedback submission error:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
      setRating(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => submitFeedback(1)}
        disabled={submitting || rating !== null}
        className={`flex h-7 w-7 items-center justify-center rounded-full transition ${
          rating === 1
            ? 'bg-emerald-500/20 text-emerald-400'
            : rating === -1
              ? 'opacity-30'
              : 'text-neutral-500 hover:bg-neutral-800 hover:text-emerald-400'
        } ${submitting || rating !== null ? 'cursor-not-allowed' : ''}`}
        title="Helpful response"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => submitFeedback(-1)}
        disabled={submitting || rating !== null}
        className={`flex h-7 w-7 items-center justify-center rounded-full transition ${
          rating === -1
            ? 'bg-red-500/20 text-red-400'
            : rating === 1
              ? 'opacity-30'
              : 'text-neutral-500 hover:bg-neutral-800 hover:text-red-400'
        } ${submitting || rating !== null ? 'cursor-not-allowed' : ''}`}
        title="Not helpful"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
