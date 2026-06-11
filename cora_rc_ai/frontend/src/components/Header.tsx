import React, { useState, useRef, useEffect } from 'react';
import { Moon, Sun, ChevronDown, Upload, BarChart2, Calendar, User as UserIcon, Settings, HelpCircle, LogOut } from 'lucide-react';
import { DEFAULT_PERSONAS, DEFAULT_USER, useChatStore } from '../store/chatStore';

export const Header: React.FC = () => {
  const { isDark, setTheme, activePersona, setPersona } = useChatStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const toggleTheme = () => {
    setTheme(!isDark);
    if (!isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-colors duration-200 relative z-50">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white">CORA</h1>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          Compliance Oriented Regulatory Assistant
        </span>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Toggle theme"
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        
        <div className="relative" ref={dropdownRef}>
          <button 
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-3 pl-4 border-l border-slate-200 dark:border-slate-700 hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-300 font-bold text-sm">
              {DEFAULT_USER.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}
            </div>
            <div className="flex flex-col items-start">
              <span className="text-sm font-semibold text-slate-900 dark:text-white">{DEFAULT_USER.name}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{activePersona}</span>
            </div>
            <ChevronDown size={16} className="text-slate-500" />
          </button>

          {isProfileOpen && (
            <div className="absolute right-0 mt-3 w-64 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden animate-fade-in z-50">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-700 dark:text-slate-300 font-bold text-sm">
                  {DEFAULT_USER.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-slate-900 dark:text-white">{DEFAULT_USER.name}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{DEFAULT_USER.email}</span>
                </div>
              </div>
              <div className="px-4 pt-4 pb-2 border-b border-slate-100 dark:border-slate-700">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                  Active role
                </label>
                <select
                  title="Select active role"
                  aria-label="Select active role"
                  value={activePersona}
                  onChange={(event) => setPersona(event.target.value)}
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {DEFAULT_PERSONAS.map((persona) => (
                    <option key={persona.id} value={persona.name}>
                      {persona.name}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Switch personas to tailor answers for checking, oversight, or audit review.
                </p>
              </div>
              <div className="p-2 flex flex-col">
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <Upload size={16} className="text-slate-400" />
                  File Upload
                </button>
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <BarChart2 size={16} className="text-slate-400" />
                  Usage Statistics
                </button>
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <Calendar size={16} className="text-slate-400" />
                  Scheduled prompts
                </button>
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <UserIcon size={16} className="text-slate-400" />
                  Personalization
                </button>
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors border-b border-slate-100 dark:border-slate-700/50 pb-4 mb-1">
                  <Settings size={16} className="text-slate-400" />
                  Settings
                </button>
                
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <HelpCircle size={16} className="text-slate-400" />
                  Help
                </button>
                <button className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                  <LogOut size={16} />
                  Log out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
