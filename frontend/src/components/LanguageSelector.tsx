import { Globe } from 'lucide-react';

export type LanguageCode =
  | 'en-IN' | 'hi-IN' | 'bn-IN' | 'ta-IN' | 'te-IN' | 'mr-IN'
  | 'gu-IN' | 'kn-IN' | 'ml-IN' | 'pa-IN' | 'or-IN' | 'ur-IN'
  | 'as-IN' | 'ks-IN' | 'ne-IN' | 'sa-IN' | 'sd-IN' | 'mai-IN'
  | 'kok-IN' | 'doi-IN' | 'mni-IN' | 'sat-IN';

type Language = {
  code: LanguageCode;
  name: string;
  nativeName: string;
};

const LANGUAGES: Language[] = [
  { code: 'en-IN', name: 'English', nativeName: 'English' },
  { code: 'hi-IN', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'bn-IN', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'ta-IN', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'te-IN', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'mr-IN', name: 'Marathi', nativeName: 'मराठी' },
  { code: 'gu-IN', name: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kn-IN', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml-IN', name: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'pa-IN', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'or-IN', name: 'Odia', nativeName: 'ଓଡ଼ିଆ' },
  { code: 'ur-IN', name: 'Urdu', nativeName: 'اردو' },
  { code: 'as-IN', name: 'Assamese', nativeName: 'অসমীয়া' },
  { code: 'ks-IN', name: 'Kashmiri', nativeName: 'कॉशुर' },
  { code: 'ne-IN', name: 'Nepali', nativeName: 'नेपाली' },
  { code: 'sa-IN', name: 'Sanskrit', nativeName: 'संस्कृतम्' },
  { code: 'sd-IN', name: 'Sindhi', nativeName: 'سنڌي' },
  { code: 'mai-IN', name: 'Maithili', nativeName: 'मैथिली' },
  { code: 'kok-IN', name: 'Konkani', nativeName: 'कोंकणी' },
  { code: 'doi-IN', name: 'Dogri', nativeName: 'डोगरी' },
  { code: 'mni-IN', name: 'Manipuri', nativeName: 'মৈতৈলোন্' },
  { code: 'sat-IN', name: 'Santali', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ' },
];

type LanguageSelectorProps = {
  value: LanguageCode;
  onChange: (language: LanguageCode) => void;
  className?: string;
};

export function LanguageSelector({ value, onChange, className = '' }: LanguageSelectorProps) {
  const selectedLanguage = LANGUAGES.find(lang => lang.code === value) ?? LANGUAGES[0];

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <label className="flex items-center gap-2 text-sm font-medium text-neutral-300">
        <Globe className="h-4 w-4" />
        Language
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value as LanguageCode)}
        className="h-10 rounded-lg border border-neutral-700 bg-neutral-900 px-3 text-sm text-neutral-100 focus:border-emerald-500 focus:outline-none"
      >
        {LANGUAGES.map(lang => (
          <option key={lang.code} value={lang.code}>
            {lang.name} ({lang.nativeName})
          </option>
        ))}
      </select>
      <p className="text-xs text-neutral-500">
        Selected: {selectedLanguage.name} - {selectedLanguage.nativeName}
      </p>
    </div>
  );
}

export { LANGUAGES };
