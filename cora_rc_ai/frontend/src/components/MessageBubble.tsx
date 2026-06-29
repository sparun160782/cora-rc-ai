import React, { useState, useRef, useEffect } from 'react';
import { Copy, ThumbsUp, ThumbsDown, Bookmark, User, ShieldCheck, Plus } from 'lucide-react';
import { useChatStore, type Message } from '../store/chatStore';

interface Props {
  message: Message;
}

export const MessageBubble: React.FC<Props> = ({ message }) => {
  const isUser = message.role === 'user';
  const [isBookmarkOpen, setIsBookmarkOpen] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [isDisliked, setIsDisliked] = useState(false);
  const [showDislikeCommentModal, setShowDislikeCommentModal] = useState(false);
  const [dislikeComment, setDislikeComment] = useState('');
  const [copied, setCopied] = useState(false);

  const bookmarkRef = useRef<HTMLDivElement>(null);
  const dislikeRef = useRef<HTMLDivElement>(null);

  const { applications, fetchApplications, addBookmark, submitMessageFeedback } = useChatStore();

  useEffect(() => {
    if (applications.length === 0) {
      void fetchApplications();
    }
  }, [applications.length, fetchApplications]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (bookmarkRef.current && !bookmarkRef.current.contains(event.target as Node)) {
        setIsBookmarkOpen(false);
      }
      if (dislikeRef.current && !dislikeRef.current.contains(event.target as Node)) {
        setShowDislikeCommentModal(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleCopy = () => {
    void navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleLike = async () => {
    setIsLiked(true);
    setIsDisliked(false);
    await submitMessageFeedback(message.id, 'LIKE');
  };

  const handleDislikeClick = () => {
    if (isDisliked) {
      setIsDisliked(false);
    } else {
      setShowDislikeCommentModal(true);
    }
  };

  const handleDislikeSubmit = async () => {
    setIsDisliked(true);
    setIsLiked(false);
    setShowDislikeCommentModal(false);
    await submitMessageFeedback(message.id, 'DISLIKE', dislikeComment);
    setDislikeComment('');
  };

  return (
    <div className={`flex gap-4 w-full ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in mb-6 group`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900 flex-shrink-0 flex items-center justify-center mt-1 border border-primary-200 dark:border-primary-800">
          <ShieldCheck className="text-primary-600 dark:text-primary-400" size={20} />
        </div>
      )}

      <div className={`max-w-[80%] flex ${isUser ? 'flex-col items-end' : 'flex-row items-start gap-4'}`}>
        {isUser ? (
          <>
            <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex-shrink-0 flex items-center justify-center mb-1">
              <User size={16} />
            </div>
            <div className="p-4 rounded-2xl bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tr-none shadow-sm">
              <div className="prose dark:prose-invert max-w-none text-sm">
                {message.content.split('\n').map((line, i) => (
                  <span key={i}>
                    {line}
                    <br />
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="p-4 rounded-2xl bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-none shadow-sm flex-1">
              {message.isStreaming && !message.content ? (
                <div className="flex space-x-2 justify-center items-center h-6">
                  <div className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="h-2 w-2 bg-slate-400 rounded-full animate-bounce"></div>
                </div>
              ) : (
                <div className="prose dark:prose-invert max-w-none text-sm">
                  {message.content.split('\n').map((line, i) => (
                    <span key={i}>
                      {line}
                      <br />
                    </span>
                  ))}
                </div>
              )}
            </div>

            {!message.isStreaming && message.content && (
              <div className="flex flex-col gap-2 pt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={handleCopy}
                  className={`p-1.5 rounded-md transition-colors ${
                    copied
                      ? 'text-green-500 bg-green-50/50 dark:bg-green-950/20'
                      : 'text-slate-400 hover:text-primary-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                  title={copied ? "Copied!" : "Copy"}
                >
                  <Copy size={16} />
                </button>
                <button
                  onClick={handleLike}
                  className={`p-1.5 rounded-md transition-colors ${
                    isLiked
                      ? 'text-green-500 bg-green-50/50 dark:bg-green-950/20'
                      : 'text-slate-400 hover:text-green-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                  title="Helpful"
                >
                  <ThumbsUp size={16} />
                </button>
                <div className="relative" ref={dislikeRef}>
                  <button
                    onClick={handleDislikeClick}
                    className={`p-1.5 rounded-md transition-colors ${
                      isDisliked
                        ? 'text-red-500 bg-red-50/50 dark:bg-red-950/20'
                        : 'text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                    title="Not Helpful"
                  >
                    <ThumbsDown size={16} />
                  </button>
                  {showDislikeCommentModal && (
                    <div className="absolute right-0 top-full mt-2 w-64 p-3 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 z-20 animate-fade-in focus-within:ring-1 focus-within:ring-primary-500">
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
                        Why was this not helpful?
                      </div>
                      <textarea
                        value={dislikeComment}
                        onChange={(e) => setDislikeComment(e.target.value)}
                        placeholder="Provide comments (optional)..."
                        className="w-full text-xs p-2 border border-slate-200 dark:border-slate-700 rounded-lg dark:bg-slate-900 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-primary-500 mb-2"
                        rows={3}
                      />
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => {
                            setShowDislikeCommentModal(false);
                            setDislikeComment('');
                          }}
                          className="px-2 py-1 text-[10px] font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleDislikeSubmit}
                          className="px-2.5 py-1 text-[10px] font-medium bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                        >
                          Submit
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                <div className="relative" ref={bookmarkRef}>
                  <button 
                    onClick={() => setIsBookmarkOpen(!isBookmarkOpen)}
                    className="p-1.5 text-slate-400 hover:text-primary-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors" 
                    title="Bookmark"
                  >
                    <Bookmark size={16} />
                  </button>
                  {isBookmarkOpen && (
                    <div className="absolute right-full top-0 mr-2 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden animate-fade-in z-10">
                      <div className="p-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400">
                        <span>Bookmark to Application</span>
                        <Plus size={14} className="cursor-pointer hover:text-primary-500" />
                      </div>
                      <div className="p-1 flex flex-col max-h-48 overflow-y-auto">
                        {(applications.length > 0 ? applications : ['OneService', 'iQMP', 'Recruitment', 'Timesheet', 'Greetings']).map(app => (
                          <button
                            key={app}
                            onClick={async () => {
                              await addBookmark(app, message.id, message.content);
                              setIsBookmarkOpen(false);
                            }}
                            className="text-left px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-md transition-colors"
                          >
                            {app}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
