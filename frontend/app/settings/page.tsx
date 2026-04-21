"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

const PROVIDERS = [
  {
    id: 'openai',
    name: 'OpenAI',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a10 10 0 1 0 10 10H12V2z"></path>
        <path d="M12 12 2.1 7.1"></path>
        <path d="M12 12v10"></path>
        <path d="m12 12 9.9 4.9"></path>
      </svg>
    ),
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' }
    ]
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="9" y1="3" x2="9" y2="21"></line>
        <line x1="15" y1="3" x2="15" y2="21"></line>
        <line x1="3" y1="9" x2="21" y2="9"></line>
        <line x1="3" y1="15" x2="21" y2="15"></line>
      </svg>
    ),
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    models: [
      { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' },
      { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet' },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku' }
    ]
  },
  {
    id: 'google',
    name: 'Google Gemini',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <circle cx="12" cy="12" r="4"></circle>
        <line x1="21.17" y1="8" x2="12" y2="8"></line>
        <line x1="3.95" y1="6.06" x2="8.54" y2="14"></line>
        <line x1="10.88" y1="21.94" x2="15.46" y2="14"></line>
      </svg>
    ),
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    models: [
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
    ]
  }
];

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [defaultModel, setDefaultModel] = useState('gpt-4o');
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    // Load from local storage on mount
    const savedKeys = localStorage.getItem('modelApiKeys');
    const savedDefault = localStorage.getItem('defaultModel');
    
    if (savedKeys) {
      try {
        setApiKeys(JSON.parse(savedKeys));
      } catch (e) {
        console.error("Failed to parse API keys", e);
      }
    }
    
    if (savedDefault) {
      setDefaultModel(savedDefault);
    }
  }, []);

  const handleKeyChange = (providerId: string, value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [providerId]: value
    }));
    setIsSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem('modelApiKeys', JSON.stringify(apiKeys));
    localStorage.setItem('defaultModel', defaultModel);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
    
    // Dispatch a custom event to notify other components (like index page)
    window.dispatchEvent(new Event('settingsUpdated'));
  };

  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased overflow-hidden">
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
        <div className="p-4 space-y-4">
          <div className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider px-2">Navigation</div>
          <nav className="space-y-1">
            <button className="w-full text-left px-3 py-2 rounded-lg bg-blue-50 text-blue-700 font-medium text-sm">
              Model Providers
            </button>
            <button className="w-full text-left px-3 py-2 rounded-lg text-[var(--text-muted)] hover:bg-gray-100/50 text-sm transition-colors">
              Appearance
            </button>
            <button className="w-full text-left px-3 py-2 rounded-lg text-[var(--text-muted)] hover:bg-gray-100/50 text-sm transition-colors">
              Knowledge Base
            </button>
          </nav>
        </div>
      </div>

      {/* Main Settings Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-4 sm:p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-main)]">Settings</h1>
            <p className="text-[var(--text-muted)] mt-1">Manage your model providers and preferences.</p>
          </div>
          
          <div className="space-y-8">
            {/* API Keys Configuration */}
            <section className="bg-white border border-[var(--border-color)] rounded-2xl shadow-sm overflow-hidden">
              <div className="p-6 border-b border-[var(--border-color)] bg-gray-50/50">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                  </svg>
                  API Keys (BYOK)
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  Configure your private API keys. These are stored locally in your browser and never sent to our servers except to proxy requests to the respective AI providers.
                </p>
              </div>
              
              <div className="p-6 divide-y divide-[var(--border-color)]">
                {PROVIDERS.map(provider => (
                  <div key={provider.id} className="py-6 first:pt-0 last:pb-0 flex flex-col md:flex-row gap-6">
                    <div className="md:w-1/3">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`w-10 h-10 rounded-xl ${provider.bgColor} ${provider.color} flex items-center justify-center`}>
                          {provider.icon}
                        </div>
                        <h3 className="font-bold text-[var(--text-main)]">{provider.name}</h3>
                      </div>
                      <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                        Required for using {provider.models.map(m => m.name).join(', ')}.
                      </p>
                    </div>
                    
                    <div className="flex-1 space-y-4">
                      <div className="flex flex-col gap-1.5">
                        <label htmlFor={`key-${provider.id}`} className="text-sm font-medium">
                          API Key
                        </label>
                        <input
                          id={`key-${provider.id}`}
                          type="password"
                          value={apiKeys[provider.id] || ''}
                          onChange={(e) => handleKeyChange(provider.id, e.target.value)}
                          placeholder={`Enter ${provider.name} API Key`}
                          className="w-full border border-[var(--border-color)] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Model Preferences */}
            <section className="bg-white border border-[var(--border-color)] rounded-2xl shadow-sm overflow-hidden">
              <div className="p-6 border-b border-[var(--border-color)] bg-gray-50/50">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                  </svg>
                  Preferences
                </h2>
              </div>
              
              <div className="p-6">
                <div className="flex flex-col gap-2">
                  <label htmlFor="default-model" className="text-sm font-medium">
                    Default Model
                  </label>
                  <p className="text-xs text-[var(--text-muted)] mb-2">Choose the model that will be selected by default when starting a new chat.</p>
                  <select
                    id="default-model"
                    value={defaultModel}
                    onChange={(e) => setDefaultModel(e.target.value)}
                    className="w-full md:w-1/2 border border-[var(--border-color)] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all bg-white appearance-none cursor-pointer"
                  >
                    {PROVIDERS.map(provider => (
                      <optgroup key={provider.id} label={provider.name}>
                        {provider.models.map(model => (
                          <option key={model.id} value={model.id}>
                            {model.name}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <div className="flex items-center justify-between p-6 bg-blue-50/50 rounded-2xl border border-blue-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-blue-900">Need help?</h4>
                  <p className="text-sm text-blue-700">Check the documentation for key generation.</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {isSaved && (
                  <span className="text-sm text-emerald-600 font-medium flex items-center gap-1.5 animate-in fade-in slide-in-from-right-2">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    Saved successfully
                  </span>
                )}
                <button
                  onClick={handleSave}
                  className="px-6 py-2.5 bg-blue-600 text-white text-sm font-bold rounded-xl hover:bg-blue-700 active:scale-95 transition-all shadow-md shadow-blue-200"
                >
                  Save All Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
