import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, ClipboardList, BarChart2, Settings } from 'lucide-react';
import Sidebar from './Sidebar';
import Header from './Header';

const BOTTOM_NAV = [
  { to: '/',             label: 'Home',     Icon: LayoutDashboard, end: true },
  { to: '/students',     label: 'Students', Icon: Users },
  { to: '/interventions',label: 'Actions',  Icon: ClipboardList },
  { to: '/analytics',    label: 'Analytics',Icon: BarChart2 },
  { to: '/settings',     label: 'Settings', Icon: Settings },
];

export default function Layout({ onLogout }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((p) => !p)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className={`main-area ${collapsed ? 'sidebar-collapsed' : ''}`}>
        <Header
          sidebarCollapsed={collapsed}
          onMobileMenuToggle={() => setMobileOpen((p) => !p)}
          onLogout={onLogout}
        />
        <main className="page-content">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom navigation bar */}
      <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
        {BOTTOM_NAV.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `mobile-bottom-nav-item${isActive ? ' active' : ''}`
            }
            onClick={() => setMobileOpen(false)}
          >
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
