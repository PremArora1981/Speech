import { useMemo, useState } from 'react';
import { VoiceChat } from './modules/chat/VoiceChat';
// import { TelephonyDashboard } from './modules/admin/TelephonyDashboard';  // Hidden: LiveKit not configured
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { LanguageSelector, type LanguageCode } from './components/LanguageSelector';

type OptimizationLevel = 'quality' | 'balanced_quality' | 'balanced' | 'balanced_speed' | 'speed';

export default function App() {
  const [sessionId, setSessionId] = useState<string>('');
  const [optimizationLevel, setOptimizationLevel] = useState<OptimizationLevel>('balanced');
  const [targetLanguage, setTargetLanguage] = useState<LanguageCode>('hi-IN');

  const sliderMarks = useMemo(
    () => [
      { value: 0, label: 'Quality', level: 'quality' as const },
      { value: 25, label: 'Balanced Quality', level: 'balanced_quality' as const },
      { value: 50, label: 'Balanced', level: 'balanced' as const },
      { value: 75, label: 'Balanced Speed', level: 'balanced_speed' as const },
      { value: 100, label: 'Max Speed', level: 'speed' as const },
    ],
    [],
  );

  const currentSliderValue = sliderMarks.find(mark => mark.level === optimizationLevel)?.value ?? 50;

  return (
    <div className='min-h-screen bg-neutral-950 text-neutral-100'>
      <main className='mx-auto flex max-w-5xl flex-col gap-6 px-4 py-10'>
        <header className='flex items-center justify-between border-b border-neutral-800 pb-6'>
          <div>
            <h1 className='text-2xl font-semibold text-neutral-50'>Speech AI Voice Chat</h1>
            <p className='text-sm text-neutral-400'>Conversational agent with real-time voice pipeline</p>
          </div>
        </header>

        <section className='grid gap-6 lg:grid-cols-2'>
          <div className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
            <h2 className='text-lg font-semibold text-neutral-100'>Performance</h2>
            <p className='mt-2 text-sm text-neutral-400'>Adjust the quality/latency mix for this session.</p>
            <div className='mt-6 flex flex-col gap-3'>
              <input
                type='range'
                min={0}
                max={100}
                step={25}
                className='w-full accent-emerald-500'
                value={currentSliderValue}
                onChange={event => {
                  const numericValue = Number(event.currentTarget.value);
                  const match = sliderMarks.find(mark => mark.value === numericValue);
                  if (match) setOptimizationLevel(match.level);
                }}
              />
              <div className='flex justify-between text-xs font-medium uppercase text-neutral-500'>
                {sliderMarks.map(mark => (
                  <span
                    key={mark.value}
                    className={mark.level === optimizationLevel ? 'text-emerald-400' : ''}
                  >
                    {mark.label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
            <LanguageSelector value={targetLanguage} onChange={setTargetLanguage} />
          </div>
        </section>

        <section className=''>
          <VoiceChat sessionId={sessionId} onSessionChange={setSessionId} optimizationLevel={optimizationLevel} />
          {/* <TelephonyDashboard /> - Temporarily hidden: LiveKit not configured */}
        </section>

        {sessionId && (
          <section>
            <AnalyticsDashboard
              sessionId={sessionId}
              optimizationLevel={optimizationLevel}
              apiUrl={import.meta.env.VITE_API_URL}
              apiKey={import.meta.env.VITE_API_KEY}
            />
          </section>
        )}
      </main>
    </div>
  );
}
