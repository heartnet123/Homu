"use client";

import React, { useState, useRef, useEffect } from 'react';

const MODELS = [
  { id: 'gpt-4', name: 'GPT-4', company: 'OpenAI', color: 'bg-blue-500', bgColor: 'bg-blue-50', textColor: 'text-blue-700', borderColor: 'border-blue-100' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5', company: 'OpenAI', color: 'bg-emerald-500', bgColor: 'bg-emerald-50', textColor: 'text-emerald-700', borderColor: 'border-emerald-100' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus', company: 'Anthropic', color: 'bg-purple-500', bgColor: 'bg-purple-50', textColor: 'text-purple-700', borderColor: 'border-purple-100' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', company: 'Google', color: 'bg-orange-500', bgColor: 'bg-orange-50', textColor: 'text-orange-700', borderColor: 'border-orange-100' }
];

export default function Home() {
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const [messages, setMessages] = useState<{role: string, content: string, sources?: string[]}[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = async () => {
    if (!query.trim() || isLoading) return;

    const newQuery = query;
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", content: newQuery }]);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: newQuery })
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "ai", content: data.answer, sources: data.sources }]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [...prev, { role: "ai", content: "Error connecting to server." }]);
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased overflow-hidden">
      {/* Sidebar Redux */}
      <div className="hidden md:flex w-64 flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
        <div className="p-4 border-b border-[var(--border-color)]">
          <button className="w-full flex items-center justify-between gap-2 border border-[var(--border-color)] bg-[var(--bg-primary)] hover:bg-gray-50 rounded-lg p-2.5 text-sm font-medium transition-colors shadow-sm text-[var(--text-main)]">
            <div className="flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <span>New Chat</span>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {/* Past Chats */}
          <div className="text-xs font-semibold text-[var(--text-muted)] mb-3 mt-2 px-3 uppercase tracking-wider">Recent</div>
          <button className="w-full text-left truncate text-sm px-3 py-2.5 rounded-lg bg-gray-100/60 text-[var(--text-main)] font-medium">
            Clean Minimalism UI
          </button>
          <button className="w-full text-left truncate text-sm px-3 py-2.5 rounded-lg hover:bg-gray-100/50 text-[var(--text-muted)] transition-colors">
            React Server Components
          </button>
          <button className="w-full text-left truncate text-sm px-3 py-2.5 rounded-lg hover:bg-gray-100/50 text-[var(--text-muted)] transition-colors">
            PostgreSQL Schema Design
          </button>
        </div>
        <div className="p-4 border-t border-[var(--border-color)]">
          <button className="flex items-center gap-3 w-full p-2 hover:bg-gray-100/50 rounded-lg transition-colors text-sm font-medium text-[var(--text-main)]">
            <div className="w-7 h-7 rounded-lg bg-blue-500 shadow-sm flex-shrink-0 flex items-center justify-center text-white text-xs">
              JD
            </div>
            <span>John Doe</span>
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-primary)] relative h-full">
        {/* Top Header Frame */}
        <div className="h-14 border-b border-[var(--border-color)] flex items-center justify-between px-4 sm:px-6 bg-[var(--bg-primary)] z-10 shrink-0">
          <div className="flex items-center gap-3">
            <button className="md:hidden p-1.5 -ml-1.5 text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-gray-50 rounded-md transition-colors">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </svg>
            </button>
            <div className="relative" ref={dropdownRef}>
              <button 
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-2 font-semibold text-lg text-[var(--text-main)] tracking-tight hover:bg-gray-50 px-2 py-1 -ml-2 rounded-lg transition-colors"
              >
                {selectedModel.name}
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`}>
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>

              {isDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-[var(--border-color)] rounded-xl shadow-lg z-50 py-1.5 overflow-hidden">
                  <div className="px-3 py-2 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border-color)] mb-1">
                    Select Model
                  </div>
                  <div className="max-h-[60vh] overflow-y-auto">
                    {MODELS.map((model) => (
                      <button
                        key={model.id}
                        onClick={() => {
                          setSelectedModel(model);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors ${selectedModel.id === model.id ? 'bg-gray-50/80' : ''}`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span className={`w-2 h-2 rounded-full ${model.color}`}></span>
                          <div>
                            <div className="text-sm font-medium text-[var(--text-main)]">
                              {model.name}
                            </div>
                            <div className="text-xs text-[var(--text-muted)]">
                              {model.company}
                            </div>
                          </div>
                        </div>
                        {selectedModel.id === model.id && (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-[var(--text-muted)] hover:text-[var(--text-main)] rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-[var(--border-color)]">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
          </div>
        </div>
        
        {/* Badges directly underneath top header */}
        <div className="bg-[var(--bg-primary)] px-4 sm:px-6 py-2 border-b border-[var(--border-color)] shadow-sm flex items-center justify-center z-10 shrink-0">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md border shadow-sm ${selectedModel.bgColor} ${selectedModel.textColor} ${selectedModel.borderColor}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${selectedModel.color}`}></span>
            {selectedModel.name} Active
          </span>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto pb-[180px]">
          <div className="max-w-3xl mx-auto flex flex-col gap-10 p-4 sm:p-6 w-full pt-8">
            {messages.length === 0 ? (
              <div className="text-center text-[var(--text-muted)] p-10 mt-10">
                <h3 className="text-xl mb-2 font-semibold">Thai Legal RAG</h3>
                <p>Start a conversation to query legal documents.</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className="flex items-start gap-4 sm:gap-6">
                  {msg.role === 'user' ? (
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-500 shadow-sm mt-0.5"></div>
                  ) : (
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-500 shadow-sm mt-0.5 flex items-center justify-center text-white">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2a10 10 0 1 0 10 10H12V2z"></path>
                        <path d="M12 12 2.1 7.1"></path>
                        <path d="M12 12v10"></path>
                        <path d="m12 12 9.9 4.9"></path>
                      </svg>
                    </div>
                  )}
                  <div className="flex-1 min-w-0 pt-1">
                    <div className="font-semibold text-sm text-[var(--text-main)] mb-1">
                      {msg.role === 'user' ? 'User' : 'AI'}
                    </div>
                    <div className="text-[var(--text-main)] text-base leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg border border-gray-200 shadow-sm">
                        <span className="font-semibold block mb-1">Sources:</span>
                        <ul className="list-disc pl-5 space-y-1">
                          {msg.sources.map((src, idx) => (
                            <li key={idx} className="break-all">{src}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex items-start gap-4 sm:gap-6">
                 <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-500 shadow-sm mt-0.5 flex items-center justify-center text-white">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                  </svg>
                </div>
                <div className="flex-1 min-w-0 pt-1">
                  <div className="font-semibold text-sm text-[var(--text-main)] mb-1">AI</div>
                  <div className="text-[var(--text-main)] text-base animate-pulse">Thinking...</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Polished Floating Input Bar */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[var(--bg-primary)] via-[var(--bg-primary)] to-transparent pt-6 pb-6 px-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative border border-[var(--border-color)] rounded-2xl bg-[var(--bg-primary)] shadow-sm flex flex-col focus-within:border-gray-300 focus-within:ring-1 focus-within:ring-gray-300 transition-all">
              <textarea 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                disabled={isLoading}
                rows={1}
                className="w-full max-h-48 py-4 px-4 resize-none outline-none text-[var(--text-main)] bg-transparent block text-[15px] placeholder:text-[var(--text-muted)] font-sans focus:ring-0 disabled:opacity-50"
                placeholder="Send a message..."
                style={{ minHeight: '56px' }}
              />
              <div className="flex justify-between items-center px-2 pb-2">
                <div className="flex gap-1 pl-1">
                  <button title="Attach file" className="p-2 text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-gray-100 rounded-xl transition-colors">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                    </svg>
                  </button>
                  <button title="Upload image" className="p-2 text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-gray-100 rounded-xl transition-colors">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <circle cx="8.5" cy="8.5" r="1.5"></circle>
                      <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                  </button>
                </div>
                <button 
                  title="Send message" 
                  onClick={handleSubmit}
                  disabled={!query.trim() || isLoading}
                  className="flex items-center justify-center p-2 rounded-xl bg-gray-100 text-[var(--text-main)] hover:bg-gray-200 transition-colors border border-[var(--border-color)] group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-70 group-hover:opacity-100">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                  </svg>
                </button>
              </div>
            </div>
            <div className="text-center mt-3">
              <p className="text-xs font-medium text-[var(--text-muted)]">AI can mistake facts. Verify important information.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
