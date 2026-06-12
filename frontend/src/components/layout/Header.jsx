import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, Menu } from 'lucide-react';

const pageTitles = {
  '/': 'Dashboard',
  '/students': 'Students',
  '/interventions': 'Interventions',
  '/alerts': 'Alerts & SMS',
  '/settings': 'Settings',
};

function getPageTitle(pathname) {
  if (pathname.startsWith('/students/')) return 'Student Detail';
  return pageTitles[pathname] || 'Dashboard';
}

export default function Header({ sidebarCollapsed, onMobileMenuToggle }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  const handleSearch = (e) => {
    if (e.key === 'Enter' && query.trim()) {
      navigate(`/students?search=${encodeURIComponent(query.trim())}`);
      setQuery(''); // clear after search
    }
  };

  return (
    <header className={`header ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="header-left">
        <button className="mobile-menu-btn" onClick={onMobileMenuToggle}>
          <Menu size={20} />
        </button>
        <h1 className="header-title">{getPageTitle(location.pathname)}</h1>
      </div>

      <div className="header-right">


        <div className="header-avatar" title="Administrator">
          AD
        </div>
      </div>
    </header>
  );
}
