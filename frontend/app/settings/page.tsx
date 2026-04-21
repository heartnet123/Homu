"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

const MODELS = [
  { id: 'gpt-4', name: 'GPT-4', company: 'OpenAI' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5', company: 'OpenAI' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus', company: 'Anthropic' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', company: 'Google' }
];

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    // Load from local storage on mount
    const savedKeys = localStorage.getItem('modelApiKeys');
    if (savedKeys) {
      try {
        setApiKeys(JSON.parse(savedKeys));
      } catch (e) {
        console.error("Failed to parse API keys", e);
      }
    }
  }, []);

  const handleKeyChange = (modelId: string, value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [modelId]: value
    }));
    setIsSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem('modelApiKeys', JSON.stringify(apiKeys));
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased">
      {/* Sidebar (simplified for settings) */}
      <div className="hidden md:flex w-64 flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
        <div className="p-4 border-b border-[var(--border-color)]">
          <Link href="/" className="w-full flex items-center justify-between gap-2 border border-[var(--border-color)] bg-[var(--bg-primary)] hover:bg-gray-50 rounded-lg p-2.5 text-sm font-medium transition-colors shadow-sm text-[var(--text-main)]">
            <div className="flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"></line>
                <polyline points="12 19 5 12 12 5"></polyline>
              </svg>
              <span>Back to Chat</span>
            </div>
          </Link>
        </div>
      </div>

      {/* Main Settings Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-8">
          <h1 className="text-2xl font-bold mb-6">Settings</h1>
          
          <div className="bg-white border border-[var(--border-color)] rounded-xl shadow-sm overflow-hidden">
            <div className="p-6 border-b border-[var(--border-color)]">
              <h2 className="text-lg font-semibold mb-1">API Keys</h2>
              <p className="text-sm text-[var(--text-muted)]">
                Configure your API keys for each model. These are stored locally in your browser.
              </p>
            </div>
            
            <div className="p-6 space-y-6">
              {MODELS.map(model => (
                <div key={model.id} className="flex flex-col gap-2">
                  <label htmlFor={`key-${model.id}`} className="text-sm font-medium flex items-center justify-between">
                    <span>{model.name} <span className="text-xs font-normal text-[var(--text-muted)] ml-2">({model.company})</span></span>
                  </label>
                  <input
                    id={`key-${model.id}`}
                    type="password"
                    value={apiKeys[model.id] || ''}
                    onChange={(e) => handleKeyChange(model.id, e.target.value)}
                    placeholder={`Enter API Key for ${model.name}`}
                    className="w-full border border-[var(--border-color)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                  />
                </div>
              ))}
            </div>

            <div className="p-6 border-t border-[var(--border-color)] bg-gray-50 flex items-center justify-end gap-4">
              {isSaved && (
                <span className="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  Saved successfully
                </span>
              )}
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
