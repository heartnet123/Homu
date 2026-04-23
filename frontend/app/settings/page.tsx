"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

import { fetchBackendCapabilities, getModelOption, getSupportedModelOptions, type ModelOption } from '../lib/models';

export default function SettingsPage() {
  const [availableModels, setAvailableModels] = useState<ModelOption[]>([getModelOption('gpt-5.4-mini')]);
  const [defaultModel, setDefaultModel] = useState('gpt-5.4-mini');
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    const loadCapabilities = async () => {
      try {
        const capabilities = await fetchBackendCapabilities();
        const supportedModels = getSupportedModelOptions(capabilities.models || []);
        if (supportedModels.length === 0) return;

        setAvailableModels(supportedModels);

        const savedDefault = localStorage.getItem('defaultModel');
        const selectedModel =
          supportedModels.find((model) => model.id === savedDefault)?.id ||
          capabilities.default_model ||
          supportedModels[0].id;

        setDefaultModel(selectedModel);
      } catch (error) {
        console.error('Failed to load backend capabilities', error);
      }
    };

    loadCapabilities();
  }, []);

  const handleSave = () => {
    localStorage.setItem('defaultModel', defaultModel);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);

    window.dispatchEvent(new Event('settingsUpdated'));
  };

  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased overflow-hidden">
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

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-4 sm:p-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-main)]">Settings</h1>
            <p className="text-[var(--text-muted)] mt-1">Manage your model providers and preferences.</p>
          </div>

          <div className="space-y-8">
            <section className="bg-white border border-[var(--border-color)] rounded-2xl shadow-sm overflow-hidden">
              <div className="p-6 border-b border-[var(--border-color)] bg-gray-50/50">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                  </svg>
                  Backend Model Support
                </h2>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  This frontend reads the supported model list from the backend so it does not offer models that the server cannot answer with.
                </p>
              </div>

              <div className="p-6 space-y-3">
                {availableModels.map((model) => (
                  <div key={model.id} className={`flex items-center justify-between rounded-xl border ${model.borderColor} ${model.bgColor} px-4 py-3`}>
                    <div className="flex items-center gap-3">
                      <span className={`h-2.5 w-2.5 rounded-full ${model.color}`}></span>
                      <div>
                        <div className="font-semibold text-[var(--text-main)]">{model.name}</div>
                        <div className="text-sm text-[var(--text-muted)]">{model.company}</div>
                      </div>
                    </div>
                    <span className={`text-sm font-medium ${model.textColor}`}>Supported</span>
                  </div>
                ))}
              </div>
            </section>

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
                    {availableModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
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
                  <p className="text-sm text-blue-700">Backend provider support is configured on the server and exposed through the capabilities endpoint.</p>
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
