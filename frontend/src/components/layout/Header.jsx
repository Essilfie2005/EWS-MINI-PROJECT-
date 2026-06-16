import { useLocation } from 'react-router-dom';
import { Menu, LogOut } from 'lucide-react';

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

  return (
    <header className={`header ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="header-left">
        <button className="mobile-menu-btn" onClick={onMobileMenuToggle}>
          <Menu size={20} />
        </button>
        <h1 className="header-title">{getPageTitle(location.pathname)}</h1>
      </div>

      <div className="header-right">
        {onLogout && (
          <button
            className="header-icon-btn"
            title="Sign out"
            onClick={onLogout}
          >
            <LogOut size={16} />
          </button>
        )}
        <div className="header-avatar" title="Administrator">
          AD
        </div>
      </div>
    </header>
  );
}
