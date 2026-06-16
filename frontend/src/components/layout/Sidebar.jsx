import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  HandHelping,
  BarChart2,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';

const navLinks = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/students', label: 'Students', icon: Users },
  { to: '/interventions', label: 'Interventions', icon: HandHelping },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }) {
  const location = useLocation();

  return (
    <>
      <div className={`sidebar-overlay ${mobileOpen ? 'visible' : ''}`} onClick={onMobileClose} />
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">
            <ShieldAlert size={20} />
          </div>
          <div className="logo-text">
            <span className="logo-title">EWS Dashboard</span>
            <span className="logo-subtitle">Dropout Early Warning</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive =
              link.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(link.to);

            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={onMobileClose}
              >
                <Icon size={20} />
                <span className="nav-label">{link.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <button className="sidebar-toggle" onClick={onToggle}>
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            <span className="sidebar-footer-text">{collapsed ? '' : 'Collapse'}</span>
          </button>
        </div>
      </aside>
    </>
  );
}
