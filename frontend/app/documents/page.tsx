"use client";

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

interface DocumentFile {
  name: string;
  size: number;
  modified: number;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingFiles, setUploadingFiles] = useState<string[]>([]);
  const [recentlyUploaded, setRecentlyUploaded] = useState<string[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/documents");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (files: File[]) => {
    const docxFiles = files.filter(f => f.name.endsWith('.docx'));
    if (docxFiles.length === 0) {
      alert("Please upload only .docx files.");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadingFiles(docxFiles.map(f => f.name));

    const formData = new FormData();
    docxFiles.forEach(file => formData.append("files", file));

    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        setUploadProgress(percent);
      }
    });

    xhr.addEventListener("load", async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setRecentlyUploaded(docxFiles.map(f => f.name));
        await fetchDocuments();
        // Clear recent highlight after 5 seconds
        setTimeout(() => setRecentlyUploaded([]), 5000);
      } else {
        alert("Upload failed.");
      }
      setIsUploading(false);
      setUploadingFiles([]);
    });

    xhr.addEventListener("error", () => {
      alert("An error occurred during upload.");
      setIsUploading(false);
      setUploadingFiles([]);
    });

    xhr.open("POST", "http://localhost:8000/api/v1/upload");
    xhr.send(formData);
  };

  const handleDelete = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

    try {
      const res = await fetch(`http://localhost:8000/api/v1/documents/${filename}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await fetchDocuments();
      }
    } catch (error) {
      console.error("Delete error:", error);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/ingest", {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Successfully indexed ${data.chunks} chunks.`);
      } else {
        alert("Sync failed.");
      }
    } catch (error) {
      console.error("Sync error:", error);
      alert("An error occurred during synchronization.");
    } finally {
      setIsSyncing(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="flex h-screen w-full bg-[var(--bg-primary)] text-[var(--text-main)] font-sans antialiased overflow-hidden">
      {/* Sidebar - Consistent with page.tsx */}
      <div className="hidden md:flex w-64 flex-col border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex-shrink-0">
        <div className="p-4 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-2 mb-4 px-1">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold tracking-wider">H</div>
            <h1 className="text-lg font-bold text-[var(--text-main)] tracking-tight">Homu</h1>
          </div>
          <Link href="/" className="w-full flex items-center gap-2 border border-transparent hover:border-[var(--border-color)] hover:bg-gray-50 rounded-lg p-2.5 text-sm font-medium transition-colors text-[var(--text-main)]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>Back to Chat</span>
          </Link>
          <Link href="/documents" className="mt-2 w-full flex items-center gap-2 border border-[var(--border-color)] bg-gray-100/60 rounded-lg p-2.5 text-sm font-semibold transition-colors text-[var(--text-main)]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            <span>Documents</span>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="text-xs font-semibold text-[var(--text-muted)] mb-3 mt-2 px-3 uppercase tracking-wider">Information</div>
          <div className="px-3 py-2 text-sm text-[var(--text-muted)] leading-relaxed">
            Manage legal documents used for the RAG knowledge base. Upload .docx files and sync to update the AI's knowledge.
          </div>
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

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-primary)] h-full overflow-y-auto">
        <header className="h-14 border-b border-[var(--border-color)] flex items-center justify-between px-6 bg-[var(--bg-primary)] sticky top-0 z-10">
          <h2 className="text-lg font-bold text-[var(--text-main)] tracking-tight">Knowledge Base</h2>
          <div className="flex items-center gap-3">
             <button 
              onClick={handleSync}
              disabled={isSyncing || documents.length === 0}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-semibold transition-all shadow-sm border ${
                isSyncing 
                ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed' 
                : 'bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700 active:scale-95'
              }`}
            >
              {isSyncing ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Syncing Knowledge...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 12c0-4.4 3.6-8 8-8 3.3 0 6.2 2 7.4 5M22 12c0 4.4-3.6 8-8 8-3.3 0-6.2-2-7.4-5"></path>
                  </svg>
                  Sync Knowledge Base
                </>
              )}
            </button>
          </div>
        </header>

        <div className="max-w-4xl mx-auto w-full p-6 space-y-8">
          {/* Upload Zone */}
          <section>
            <h3 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-widest mb-4">Batch Upload</h3>
            <div 
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center transition-all cursor-pointer group ${
                dragActive 
                ? 'border-blue-500 bg-blue-50/50' 
                : 'border-[var(--border-color)] hover:border-blue-400 hover:bg-gray-50/50'
              }`}
            >
              <input 
                type="file" 
                multiple 
                accept=".docx" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileInput}
              />
              <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 mb-4 group-hover:scale-110 transition-transform">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <p className="text-lg font-bold text-[var(--text-main)] mb-1">Click or drag documents here</p>
              <p className="text-[var(--text-muted)] text-sm">Only Thai legal documents in .docx format</p>
              
              {isUploading && (
                <div className="absolute inset-0 bg-white/90 backdrop-blur-md rounded-3xl flex flex-col items-center justify-center p-8 z-20">
                  <div className="w-full max-w-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold text-blue-600 uppercase tracking-tighter">Uploading {uploadingFiles.length} file{uploadingFiles.length > 1 ? 's' : ''}</span>
                      <span className="text-sm font-black text-blue-700">{uploadProgress}%</span>
                    </div>
                    <div className="w-full h-3 bg-blue-100/50 rounded-full overflow-hidden mb-6 border border-blue-100 shadow-inner">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-300 ease-out shadow-[0_0_10px_rgba(37,99,235,0.4)]" 
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                    <div className="space-y-2 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                      {uploadingFiles.map((name, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs font-medium text-gray-600 bg-white/50 p-2 rounded-lg border border-white/80 shrink-0 animate-in fade-in slide-in-from-bottom-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
                            <path d="M20 6L9 17l-5-5"></path>
                          </svg>
                          <span className="truncate">{name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Document List */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-widest">Available Documents</h3>
              <span className="text-xs font-bold px-2 py-1 bg-gray-100 text-gray-600 rounded-md border border-gray-200 uppercase">
                {documents.length} Files
              </span>
            </div>
            
            <div className="bg-white border border-[var(--border-color)] rounded-2xl overflow-hidden shadow-sm">
              {documents.length === 0 ? (
                <div className="p-12 text-center">
                  <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center text-gray-300 mx-auto mb-3">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <line x1="3" y1="9" x2="21" y2="9"></line>
                    </svg>
                  </div>
                  <p className="text-[var(--text-muted)] font-medium">No documents uploaded yet.</p>
                </div>
              ) : (
                <div className="divide-y divide-[var(--border-color)]">
                  {documents.map((doc, idx) => (
                    <div key={idx} className={`flex items-center justify-between p-4 hover:bg-gray-50/50 transition-all group border-l-4 ${recentlyUploaded.includes(doc.name) ? 'border-l-emerald-500 bg-emerald-50/30' : 'border-l-transparent'}`}>
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 shrink-0">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                          </svg> 
                        </div>
                        <div className="truncate">
                          <p className="font-bold text-[var(--text-main)] truncate">{doc.name}</p>
                          <div className="flex items-center gap-3 mt-0.5">
                            <span className="text-xs text-[var(--text-muted)]">{formatSize(doc.size)}</span>
                            <span className="w-1 h-1 rounded-full bg-gray-300"></span>
                            <span className="text-xs text-[var(--text-muted)]">
                              Modified {new Date(doc.modified * 1000).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button 
                        onClick={() => handleDelete(doc.name)}
                        className="p-2.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                        title="Delete Document"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                          <line x1="10" y1="11" x2="10" y2="17"></line>
                          <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Guidelines / Info */}
          <section className="bg-amber-50/50 border border-amber-100 rounded-2xl p-6">
            <h4 className="flex items-center gap-2 text-amber-800 font-bold mb-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              Synchronization Required
            </h4>
            <p className="text-sm text-amber-700 leading-relaxed">
              Uploading a document adds it to the storage, but the AI won't be able to "read" it until you click **Sync Knowledge Base**. This process splits the documents into chunks and generates mathematical embeddings for vector search.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
