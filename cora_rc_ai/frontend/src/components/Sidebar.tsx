import React from 'react';
import { MessageSquarePlus, Search, FolderOpen, Bookmark, ChevronDown, MessageSquare, Trash2 } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import { Link, useNavigate } from 'react-router-dom';

export const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const {
    clearChat,
    sessions,
    fetchSessions,
    loadSession,
    deleteSession,
    bookmarks,
    fetchBookmarks,
  } = useChatStore();

  React.useEffect(() => {
    void fetchSessions();
    void fetchBookmarks();
  }, [fetchSessions, fetchBookmarks]);

  const handleNewChat = () => {
    clearChat();
    navigate('/');
  };

  const handleLoadSession = async (sessionId: string) => {
    await loadSession(sessionId);
    navigate('/');
  };

  return (
    <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 h-screen flex flex-col transition-colors duration-200">
      <div className="p-4 flex gap-2">
        <button
          onClick={handleNewChat}
          className="flex-1 flex items-center justify-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md py-2 px-4 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm text-sm font-medium"
        >
          <MessageSquarePlus size={16} className="text-primary-600" />
          New chat
        </button>
        <button title="Toggle sidebar layout" aria-label="Toggle sidebar layout" className="p-2 border border-slate-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="9" y1="3" x2="9" y2="21" /></svg>
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        <ul className="space-y-1 px-2">
          <li>
            <button className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md transition-colors">
              <Search size={16} />
              Search chats
            </button>
          </li>
          <li>
            <Link to="/documents" className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md transition-colors">
              <FolderOpen size={16} />
              Manage Files
            </Link>
          </li>
        </ul>

        <div className="mt-6">
          <div className="px-5 mb-2 flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Regulatory Bookmarks</span>
            <ChevronDown size={14} />
          </div>
          <ul className="space-y-1 px-2">
            <li>
              <button className="w-full flex items-center justify-between px-3 py-2 text-sm bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-white rounded-md transition-colors">
                <div className="flex items-center gap-3">
                  <Bookmark size={16} className="text-primary-600" />
                  All Bookmarks
                </div>
                <div className="w-4 h-4 rounded-full border border-primary-500 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-primary-500"></div>
                </div>
              </button>
            </li>
            {bookmarks.length === 0 ? (
              <li className="px-9 py-2 text-xs text-slate-500 dark:text-slate-400">
                No bookmarked answers yet
              </li>
            ) : (
              bookmarks.map((bookmark) => {
                const appName = bookmark.assessment?.application || 'General';
                const previewText = bookmark.assessment?.content || '';
                return (
                  <li key={bookmark.bookmark_id} className="relative group/bookmark flex items-center justify-between rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                    <button
                      onClick={async () => {
                        if (bookmark.session_id) {
                          await loadSession(bookmark.session_id);
                          navigate('/');
                        }
                      }}
                      className="w-full text-left px-9 py-2 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white transition-colors truncate pr-8"
                      title={`${appName}: ${previewText}`}
                    >
                      <span className="font-semibold text-primary-600 dark:text-primary-400 mr-1">
                        [{appName}]
                      </span>
                      {previewText.length > 20 ? `${previewText.slice(0, 20)}...` : previewText}
                    </button>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (confirm('Remove this bookmark?')) {
                          const { removeBookmark } = useChatStore.getState();
                          await removeBookmark(bookmark.bookmark_id);
                        }
                      }}
                      className="absolute right-1 opacity-0 group-hover/bookmark:opacity-100 p-1 rounded-md text-slate-400 hover:text-red-500 transition-all ml-auto"
                      title="Remove Bookmark"
                    >
                      <Trash2 size={12} />
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>

        <div className="mt-6">
          <div className="px-5 mb-2 flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Your Chats</span>
            <ChevronDown size={14} />
          </div>
          <ul className="space-y-1 px-2">
            {sessions.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">
                No persisted chats yet
              </li>
            ) : (
              sessions.map((session) => (
                <li key={session.session_id} className="group/session relative flex items-center">
                  <button
                    onClick={() => void handleLoadSession(session.session_id)}
                    className="w-full text-left px-3 py-2 pr-10 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                  >
                    <div className="flex items-start gap-3 text-sm text-slate-700 dark:text-slate-300">
                      <MessageSquare size={16} className="mt-0.5 shrink-0" />
                      <div className="min-w-0 pr-2">
                        <div className="truncate font-medium">{session.title || 'New chat'}</div>
                        <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                          {session.last_message_preview || session.persona || 'Persisted session'}
                        </div>
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm('Are you sure you want to delete this chat session?')) {
                        void deleteSession(session.session_id);
                      }
                    }}
                    className="absolute right-2 opacity-0 group-hover/session:opacity-100 p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-slate-300 dark:hover:bg-slate-750 transition-all"
                    title="Delete Chat"
                  >
                    <Trash2 size={13} />
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      </nav>
    </aside>
  );
};
