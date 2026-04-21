"use client";

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

const ALL_MODELS = [
  { id: 'gpt-5.4', name: 'GPT-5.4', company: 'OpenAI', color: 'bg-emerald-600', bgColor: 'bg-emerald-50', textColor: 'text-emerald-800', borderColor: 'border-emerald-200' },
  { id: 'gpt-5.4-mini', name: 'GPT-5.4 Mini', company: 'OpenAI', color: 'bg-emerald-400', bgColor: 'bg-emerald-50', textColor: 'text-emerald-600', borderColor: 'border-emerald-100' },
  { id: 'gpt-4o', name: 'GPT-4o', company: 'OpenAI', color: 'bg-emerald-500', bgColor: 'bg-emerald-50', textColor: 'text-emerald-700', borderColor: 'border-emerald-100' },
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', company: 'OpenAI', color: 'bg-emerald-500', bgColor: 'bg-emerald-50', textColor: 'text-emerald-700', borderColor: 'border-emerald-100' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', company: 'OpenAI', color: 'bg-emerald-500', bgColor: 'bg-emerald-50', textColor: 'text-emerald-700', borderColor: 'border-emerald-100' },
  { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', company: 'Anthropic', color: 'bg-purple-500', bgColor: 'bg-purple-50', textColor: 'text-purple-700', borderColor: 'border-purple-100' },
  { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', company: 'Anthropic', color: 'bg-purple-500', bgColor: 'bg-purple-50', textColor: 'text-purple-700', borderColor: 'border-purple-100' },
  { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', company: 'Anthropic', color: 'bg-purple-500', bgColor: 'bg-purple-50', textColor: 'text-purple-700', borderColor: 'border-purple-100' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', company: 'Google', color: 'bg-blue-500', bgColor: 'bg-blue-50', textColor: 'text-blue-700', borderColor: 'border-blue-100' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', company: 'Google', color: 'bg-blue-500', bgColor: 'bg-blue-50', textColor: 'text-blue-700', borderColor: 'border-blue-100' }
];

export default function Home() {
  const [selectedModel, setSelectedModel] = useState(ALL_MODELS[0]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const loadSettings = () => {
    const savedDefault = localStorage.getItem('defaultModel');
    if (savedDefault) {
      const model = ALL_MODELS.find(m => m.id === savedDefault);
      if (model) setSelectedModel(model);
    }
  };

  useEffect(() => {
    loadSettings();
    window.addEventListener('settingsUpdated', loadSettings);
    return () => window.removeEventListener('settingsUpdated', loadSettings);
  }, []);

  const [messages, setMessages] = useState<{role: string, content: string, sources?: string[], isError?: boolean, isRetryable?: boolean, originalQuery?: string, needsClarification?: boolean}[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [recentThreads, setRecentThreads] = useState<any[]>([]);

  const fetchThreads = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/threads");
      if (res.ok) {
        const data = await res.json();
        setRecentThreads(data);
      }
    } catch (e) {
      console.error("Failed to fetch threads", e);
    }
  };

  const loadThread = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/threads/${id}`);
      if (res.ok) {
        const data = await res.json();
        const mappedMessages = data.map((m: any) => ({
          role: m.role,
          content: m.content,
          sources: m.sources,
          needsClarification: m.needs_clarification
        }));
        setMessages(mappedMessages);
        setCurrentThreadId(id);
        if (window.innerWidth < 768) setIsDropdownOpen(false); // Close sidebar on mobile if it existed
      }
    } catch (e) {
      console.error("Failed to load thread", e);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = async (retryQuery?: string | React.MouseEvent | React.KeyboardEvent) => {
    const queryToSend = typeof retryQuery === "string" ? retryQuery : query;
    if (!queryToSend.trim() || isLoading) return;

    if (typeof retryQuery !== "string") {
      setQuery("");
      setMessages((prev) => [...prev, { role: "user", content: queryToSend }]);
    } else {
      setMessages((prev) => prev.filter(msg => !msg.isError));
    }

    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ query: queryToSend, thread_id: currentThreadId || undefined, model: selectedModel.id })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      setMessages((prev) => [...prev, { role: "ai", content: "" }]);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No readable stream");

      const decoder = new TextDecoder("utf-8");
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          
          buffer = lines.pop() || "";
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (!dataStr) continue;
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === 'token') {
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsg = newMessages[newMessages.length - 1];
                    if (lastMsg && lastMsg.role === 'ai') {
                      lastMsg.content += parsed.content;
                    }
                    return newMessages;
                  });
                } else if (parsed.type === 'metadata') {
                  if (parsed.thread_id && parsed.thread_id !== currentThreadId) {
                    setCurrentThreadId(parsed.thread_id);
                    fetchThreads();
                  }
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsg = newMessages[newMessages.length - 1];
                    if (lastMsg && lastMsg.role === 'ai') {
                      lastMsg.sources = parsed.sources;
                      lastMsg.needsClarification = parsed.needs_clarification;
                      if (parsed.needs_clarification && !lastMsg.content) {
                          lastMsg.content = "กรุณาให้ข้อมูลเพิ่มเติมเพื่อให้เราช่วยเหลือได้อย่างถูกต้อง";
                      }
                      if (!lastMsg.content && !parsed.needs_clarification) {
                          lastMsg.content = "ไม่พบคำตอบสำหรับคำถามของคุณ กรุณาลองใช้คำถามที่แตกต่างออกไป";
                      }
                    }
                    return newMessages;
                  });
                } else if (parsed.type === 'error') {
                   setMessages((prev) => {
                    const newMessages = [...prev];
                    const lastMsg = newMessages[newMessages.length - 1];
                    if (lastMsg && lastMsg.role === 'ai') {
                      lastMsg.content += "\n[ข้อผิดพลาด: " + parsed.content + "]";
                    }
                    return newMessages;
                  });
                }
              } catch (e) {
                console.error("Failed to parse SSE JSON", e, dataStr);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setMessages((prev) => [...prev, { 
        role: "ai", 
        content: "เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง",
        isError: true,
        isRetryable: true,
        originalQuery: queryToSend
      }]);
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased overflow-hidden">
      {/* Sidebar Redux */}
      <div className="hidden md:flex w-64 flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-2 mb-4 px-1">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold tracking-wider">H</div>
            <h1 className="text-lg font-bold text-[var(--text-main)] tracking-tight">Homu</h1>
          </div>
          <button onClick={() => { setMessages([]); setQuery(""); setCurrentThreadId(null); }} className="w-full flex items-center justify-between gap-2 border border-[var(--border-color)] bg-[var(--bg-primary)] hover:bg-gray-50 rounded-lg p-2.5 text-sm font-medium transition-colors shadow-sm text-[var(--text-main)]">
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
          <Link href="/documents" className="mt-2 w-full flex items-center gap-2 border border-transparent hover:border-[var(--border-color)] hover:bg-gray-50 rounded-lg p-2.5 text-sm font-medium transition-colors text-[var(--text-main)]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <span>Documents</span>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {/* Past Chats */}
          <div className="text-xs font-semibold text-[var(--text-muted)] mb-3 mt-2 px-3 uppercase tracking-wider">Recent</div>
          {recentThreads.map(thread => (
            <button 
              key={thread.id} 
              onClick={() => loadThread(thread.id)} 
              className={`w-full text-left truncate text-sm px-3 py-2.5 rounded-lg transition-colors ${currentThreadId === thread.id ? 'bg-gray-100/60 text-[var(--text-main)] font-medium' : 'hover:bg-gray-100/50 text-[var(--text-muted)]'}`}
            >
              {thread.title}
            </button>
          ))}
          {recentThreads.length === 0 && (
            <div className="px-3 text-xs text-[var(--text-muted)]">No recent chats</div>
          )}
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
                    {ALL_MODELS.map((model) => (
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
            <Link href="/settings" className="p-2 text-[var(--text-muted)] hover:text-[var(--text-main)] rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-[var(--border-color)]">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </Link>
          </div>

        </div>
        

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto pb-[180px]">
          <div className="max-w-3xl mx-auto flex flex-col gap-10 p-4 sm:p-6 w-full pt-8">
            {messages.length === 0 ? (
              <div className="text-center text-[var(--text-muted)] p-10 mt-10">
                <h3 className="text-xl mb-2 font-semibold">Homu — ที่ปรึกษากฎหมายไทย</h3>
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
                    {msg.needsClarification && (
                      <div className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-50 text-orange-700 text-sm font-medium border border-orange-100">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                        ต้องการข้อมูลเพิ่มเติม
                      </div>
                    )}
                    {msg.isError && msg.isRetryable && (
                      <button 
                        onClick={() => handleSubmit(msg.originalQuery)}
                        className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm font-medium hover:bg-red-100 transition-colors border border-red-100"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
                        ลองใหม่อีกครั้ง
                      </button>
                    )}
                    {msg.sources && msg.sources.length > 0 && (
                      <details className="mt-4 bg-gray-50/50 rounded-xl border border-gray-200/80 overflow-hidden group">
                        <summary className="px-4 py-3 text-sm font-semibold text-gray-700 cursor-pointer hover:bg-gray-50 flex items-center justify-between list-none [&::-webkit-details-marker]:hidden transition-colors">
                          <span className="flex items-center gap-2.5">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"></path></svg>
                            Sources ({msg.sources.length})
                          </span>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-200 group-open:rotate-180 text-gray-400"><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </summary>
                        <div className="px-4 pb-4 pt-1 space-y-3">
                          {msg.sources.map((src, idx) => {
                            let remaining = src.trim();
                            const tags = [];
                            while (remaining.startsWith('[')) {
                              const endIdx = remaining.indexOf(']');
                              if (endIdx !== -1) {
                                tags.push(remaining.substring(1, endIdx).trim());
                                remaining = remaining.substring(endIdx + 1).trim();
                              } else {
                                break;
                              }
                            }
                            return (
                              <div key={idx} className="bg-white p-3.5 rounded-lg border border-gray-200 shadow-sm">
                                {tags.length > 0 && (
                                  <div className="flex flex-wrap gap-2 mb-2">
                                    {tags.map((tag, tIdx) => (
                                      <span key={tIdx} className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-gray-100 text-gray-600 border border-gray-200 uppercase tracking-wider">
                                        {tag}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                <div className="text-[13px] text-gray-700 leading-relaxed whitespace-pre-wrap">
                                  {remaining || src}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </details>
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
