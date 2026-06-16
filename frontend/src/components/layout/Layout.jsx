import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

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
    </div>
  );
}
