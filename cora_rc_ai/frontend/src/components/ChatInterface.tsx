import React, { useState, useRef, useEffect } from 'react';
import { Send, Shield } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { MessageBubble } from './MessageBubble';
import { streamAgentResponse } from '../services/sse';

export const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { messages, sessionId, activePersona } = useChatStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const message = input;
    setInput('');
    setIsSending(true);

    try {
      await streamAgentResponse(message, sessionId);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-slate-50 dark:bg-slate-900 transition-colors duration-200">
      
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 animate-fade-in">
          <div className="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex items-center justify-center mb-6">
            <Shield className="text-primary-600" size={32} />
          </div>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">CORA</h2>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400 text-center mb-6 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Online
          </p>
          <p className="text-slate-600 dark:text-slate-400 text-center max-w-md mb-8">
            AI-powered compliance guidance for regulatory review, oversight, and audit evidence.
          </p>

          <div className="mb-6 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-600 dark:text-slate-300 shadow-sm">
            Active role: <span className="font-semibold text-slate-900 dark:text-white">{activePersona}</span>
          </div>

          <div className="w-full max-w-2xl bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-8">
            <form onSubmit={handleSubmit} className="relative flex items-center w-full">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask me anything... e.g., What is the Process approach to ISMS"
                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white rounded-xl py-4 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-primary-500 shadow-sm transition-all"
                disabled={isSending}
              />
              <button
                type="submit"
                title="Send message"
                aria-label="Send message"
                disabled={!input.trim() || isSending}
                className="absolute right-2 p-2 bg-slate-500 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto p-4 md:p-8">
            <div className="max-w-4xl mx-auto flex flex-col gap-2">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
          <div className="p-4 md:p-6 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
            <div className="max-w-4xl mx-auto">
              <div className="flex justify-between items-center mb-2 px-2 text-xs font-medium text-slate-400 dark:text-slate-500">
                <div className="flex items-center gap-4">
                  <span>💬 {messages.length} messages</span>
                  <span>Role: {activePersona}</span>
                  <span>Session: {sessionId ? 'Persisted' : 'New'}</span>
                </div>
                <span className="text-green-600 dark:text-green-500 font-semibold">Database-backed history enabled</span>
              </div>
              <form onSubmit={handleSubmit} className="relative flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Respond to the Agent, refine the plan, or type 'Looks good'..."
                  className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white rounded-xl py-3 pl-4 pr-12 focus:outline-none focus:border-slate-300 shadow-sm transition-all text-sm"
                  disabled={isSending}
                />
                <button
                  type="submit"
                  title="Send message"
                  aria-label="Send message"
                  disabled={!input.trim() || isSending}
                  className="absolute right-2 p-2 bg-slate-500 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
