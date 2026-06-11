import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import {
  fetchChatSession,
  fetchChatSessions,
  deleteChatSession,
  fetchBookmarks,
  createBookmark,
  deleteBookmark,
  submitFeedback,
  fetchApplications,
  type ChatSessionSummary,
  type BookmarkRecord
} from '../services/api';

export interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  citations?: any[];
}

export interface PersonaDefinition {
  id: string;
  name: string;
  action: string;
  needs: string[];
}

export const DEFAULT_PERSONAS: PersonaDefinition[] = [
  {
    id: 'compliance_officer',
    name: 'Compliance Officer',
    action: 'Day-to-day checking',
    needs: ['Fast answers', 'Citations'],
  },
  {
    id: 'compliance_head',
    name: 'Compliance Head',
    action: 'Oversight and reporting',
    needs: ['Summary reports', 'Risk trends'],
  },
  {
    id: 'internal_auditor',
    name: 'Internal Auditor',
    action: 'Post-review',
    needs: ['Audit trail', 'Evidence and sources'],
  },
];

export const DEFAULT_USER = {
  id: 'default_user',
  name: 'Arun S.P',
  email: 'arun.sp@cora.com',
};

interface ChatState {
  messages: Message[];
  sessions: ChatSessionSummary[];
  bookmarks: BookmarkRecord[];
  applications: string[];
  isDark: boolean;
  activePersona: string;
  sessionId: string | null;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string, isDone?: boolean) => void;
  replaceMessages: (messages: Message[]) => void;
  setTheme: (isDark: boolean) => void;
  setPersona: (persona: string) => void;
  setSessionId: (id: string) => void;
  fetchSessions: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  clearChat: () => void;
  fetchBookmarks: () => Promise<void>;
  fetchApplications: () => Promise<void>;
  addBookmark: (application: string, messageId: string, content: string) => Promise<void>;
  removeBookmark: (bookmarkId: string) => Promise<void>;
  submitMessageFeedback: (messageId: string, rating: 'LIKE' | 'DISLIKE', comments?: string) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessions: [],
      bookmarks: [],
      applications: [],
      isDark: false,
      activePersona: DEFAULT_PERSONAS[0].name,
      sessionId: null,
      addMessage: (message) => 
        set((state) => ({ messages: [...state.messages, message] })),
      updateLastMessage: (content, isDone = false) =>
        set((state) => {
          const messages = [...state.messages];
          if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            if (lastMessage.role === 'agent') {
              lastMessage.content = content;
              if (isDone) lastMessage.isStreaming = false;
            }
          }
          return { messages };
        }),
      replaceMessages: (messages) => set({ messages }),
      setTheme: (isDark) => set({ isDark }),
      setPersona: (activePersona) => set({ activePersona }),
      setSessionId: (sessionId) => set({ sessionId }),
      fetchSessions: async () => {
        const sessions = await fetchChatSessions(DEFAULT_USER.id);
        set({ sessions });
      },
      loadSession: async (sessionId) => {
        const detail = await fetchChatSession(sessionId);
        set({
          sessionId,
          activePersona: detail.session.persona || DEFAULT_PERSONAS[0].name,
          messages: detail.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
            timestamp: message.timestamp,
            citations: message.citations,
          })),
        });
      },
      deleteSession: async (sessionId) => {
        await deleteChatSession(sessionId);
        set((state) => {
          const sessions = state.sessions.filter((s) => s.session_id !== sessionId);
          const nextSessionId = state.sessionId === sessionId ? null : state.sessionId;
          const nextMessages = state.sessionId === sessionId ? [] : state.messages;
          return { sessions, sessionId: nextSessionId, messages: nextMessages };
        });
      },
      clearChat: () => set({ messages: [], sessionId: null }),
      fetchBookmarks: async () => {
        const bookmarks = await fetchBookmarks(DEFAULT_USER.id);
        set({ bookmarks });
      },
      fetchApplications: async () => {
        const applications = await fetchApplications();
        set({ applications });
      },
      addBookmark: async (application, messageId, content) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;
        await createBookmark(sessionId, application, messageId, content, DEFAULT_USER.id);
        const bookmarks = await fetchBookmarks(DEFAULT_USER.id);
        set({ bookmarks });
      },
      removeBookmark: async (bookmarkId) => {
        await deleteBookmark(bookmarkId);
        set((state) => ({
          bookmarks: state.bookmarks.filter((b) => b.bookmark_id !== bookmarkId)
        }));
      },
      submitMessageFeedback: async (messageId, rating, comments) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;
        await submitFeedback(sessionId, messageId, rating, comments, DEFAULT_USER.id);
      },
    }),
    {
      name: 'cora-chat-storage',
      partialize: (state) => ({ 
        messages: state.messages, 
        isDark: state.isDark, 
        activePersona: state.activePersona,
        sessionId: state.sessionId,
      }),
    }
  )
);
