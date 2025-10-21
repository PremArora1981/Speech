import React, { useEffect, useState } from 'react';
import {
  fetchPromptTemplates,
  fetchSystemPrompts,
  createSystemPrompt,
  updateSystemPrompt,
  SystemPrompt,
} from '../lib/api';

type SystemPromptEditorProps = {
  value: string;
  onChange: (promptId: string, promptText: string) => void;
  onSave?: (prompt: SystemPrompt) => void;
};

export const SystemPromptEditor: React.FC<SystemPromptEditorProps> = ({
  value,
  onChange,
  onSave,
}) => {
  const [promptText, setPromptText] = useState(value);
  const [templates, setTemplates] = useState<SystemPrompt[]>([]);
  const [userPrompts, setUserPrompts] = useState<SystemPrompt[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [showTemplates, setShowTemplates] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveCategory, setSaveCategory] = useState('general');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTemplates();
    loadUserPrompts();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await fetchPromptTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const loadUserPrompts = async () => {
    try {
      const data = await fetchSystemPrompts({ is_template: false });
      setUserPrompts(data);
    } catch (err) {
      console.error('Failed to load user prompts:', err);
    }
  };

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    setPromptText(newText);
    onChange('', newText);
  };

  const handleLoadTemplate = (template: SystemPrompt) => {
    setPromptText(template.prompt_text);
    setSelectedTemplate(template.id);
    onChange(template.id, template.prompt_text);
    setShowTemplates(false);
  };

  const handleSavePrompt = async () => {
    if (!saveName.trim()) {
      setError('Please enter a name for the prompt');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const newPrompt = await createSystemPrompt({
        name: saveName,
        prompt_text: promptText,
        category: saveCategory,
        is_default: false,
      });

      // Reload user prompts
      await loadUserPrompts();

      setShowSaveDialog(false);
      setSaveName('');
      setSaveCategory('general');

      if (onSave) {
        onSave(newPrompt);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  // Extract variables from prompt text
  const extractVariables = (text: string): string[] => {
    const matches = text.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g);
    if (!matches) return [];
    return Array.from(new Set(matches.map((m) => m.slice(1, -1))));
  };

  const variables = extractVariables(promptText);
  const charCount = promptText.length;

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">System Prompt</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
          >
            {showTemplates ? 'Hide Templates' : 'Load Template'}
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            Save as New
          </button>
        </div>
      </div>

      {/* Template Library */}
      {showTemplates && (
        <div className="mb-4 p-4 bg-gray-50 rounded-md max-h-64 overflow-y-auto">
          <h4 className="font-medium text-gray-900 mb-3">Templates</h4>
          <div className="space-y-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className="p-3 bg-white border border-gray-200 rounded cursor-pointer hover:border-blue-500"
                onClick={() => handleLoadTemplate(template)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h5 className="font-medium text-gray-900">{template.name}</h5>
                    <p className="text-xs text-gray-500 mt-1">
                      Category: {template.category}
                    </p>
                  </div>
                  {template.variables.length > 0 && (
                    <div className="flex gap-1">
                      {template.variables.map((v) => (
                        <span
                          key={v}
                          className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="mb-2">
        <textarea
          value={promptText}
          onChange={handlePromptChange}
          placeholder="Enter your system prompt here..."
          className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-y"
        />
      </div>

      {/* Character Count & Variables */}
      <div className="flex justify-between items-center text-sm text-gray-600 mb-4">
        <div>
          <span className={charCount > 2000 ? 'text-red-600 font-medium' : ''}>
            {charCount} / 2000 characters
          </span>
          {charCount > 2000 && (
            <span className="ml-2 text-red-600">⚠ Prompt is too long</span>
          )}
        </div>
        {variables.length > 0 && (
          <div className="flex gap-1 items-center">
            <span>Variables:</span>
            {variables.map((v) => (
              <span key={v} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                {'{'}
                {v}
                {'}'}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Save System Prompt</h3>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded mb-4 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="My Custom Prompt"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={saveCategory}
                  onChange={(e) => setSaveCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="general">General</option>
                  <option value="customer_support">Customer Support</option>
                  <option value="sales">Sales</option>
                  <option value="technical">Technical</option>
                  <option value="scheduling">Scheduling</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setError(null);
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSavePrompt}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* My Prompts */}
      {userPrompts.length > 0 && (
        <div className="mt-4 p-4 bg-gray-50 rounded-md">
          <h4 className="font-medium text-gray-900 mb-3">My Saved Prompts</h4>
          <div className="space-y-2">
            {userPrompts.map((prompt) => (
              <div
                key={prompt.id}
                className="p-3 bg-white border border-gray-200 rounded cursor-pointer hover:border-blue-500"
                onClick={() => handleLoadTemplate(prompt)}
              >
                <div className="flex justify-between">
                  <h5 className="font-medium text-gray-900">{prompt.name}</h5>
                  <span className="text-xs text-gray-500">{prompt.category}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
