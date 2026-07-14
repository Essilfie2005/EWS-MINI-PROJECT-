import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Menu, LogOut, Sun, Moon } from 'lucide-react';

const pageTitles = {
  '/': 'Dashboard',
  '/students': 'Students',
  '/interventions': 'Interventions',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

function getPageTitle(pathname) {
  if (pathname.startsWith('/students/')) return 'Student Detail';
  return pageTitles[pathname] || 'Dashboard';
}

export default function Header({ sidebarCollapsed, onMobileMenuToggle, onLogout }) {
  const location = useLocation();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [theme, setTheme] = useState(() => localStorage.getItem('ews_theme') || 'dark');

  // Apply theme on mount and change
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ews_theme', theme);
  }, [theme]);

  // Online/offline listeners
  useEffect(() => {
    const handleOnline  = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online',  handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online',  handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const toggleTheme = () => setTheme(t => (t === 'dark' ? 'light' : 'dark'));

  return (
    <header className={`header ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="header-left">
        <button className="mobile-menu-btn" onClick={onMobileMenuToggle}>
          <Menu size={20} />
        </button>
        <h1 className="header-title">{getPageTitle(location.pathname)}</h1>
      </div>

      <div className="header-right">
        {/* Online / Offline indicator */}
        <div
          title={isOnline ? 'Browser online' : 'Browser offline'}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
            background:  isOnline ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)',
            border: `1px solid ${isOnline ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`,
            color: isOnline ? '#10b981' : '#f43f5e',
            userSelect: 'none',
          }}
        >
          <span
            style={{
              width: 7, height: 7, borderRadius: '50%',
              background: isOnline ? '#10b981' : '#f43f5e',
              boxShadow: isOnline ? '0 0 6px #10b981' : '0 0 6px #f43f5e',
              flexShrink: 0,
            }}
          />
          {isOnline ? 'Online' : 'Offline'}
        </div>

        {/* Dark / Light mode toggle */}
        <button
          className="header-icon-btn"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={toggleTheme}
          style={{ color: theme === 'dark' ? '#fbbf24' : '#6366f1' }}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {onLogout && (
          <button className="header-icon-btn" title="Sign out" onClick={onLogout}>
            <LogOut size={16} />
          </button>
        )}
        <div className="header-avatar" title="Administrator">AD</div>
      </div>
    </header>
  );
}
