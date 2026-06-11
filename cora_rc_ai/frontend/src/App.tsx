import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatInterface } from './components/ChatInterface';
import { DocumentManager } from './pages/DocumentManager';
import { useChatStore } from './store/chatStore';

const AppLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-900 transition-colors duration-200">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header />
        {children}
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const { isDark } = useChatStore();

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={
          <AppLayout>
            <ChatInterface />
          </AppLayout>
        } />
        <Route path="/documents" element={
          <AppLayout>
            <DocumentManager />
          </AppLayout>
        } />
      </Routes>
    </Router>
  );
};

export default App;
