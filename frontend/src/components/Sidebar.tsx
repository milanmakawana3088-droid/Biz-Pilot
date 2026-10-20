import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Boxes,
  History,
  ShoppingBag,
  TrendingUp,
  BarChart3,
  ShieldCheck,
  Building2,
  LogOut,
  Warehouse as WarehouseIcon,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user, activeWarehouse, warehouses, setActiveWarehouse, logout } = useAuth();

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/products', label: 'Products', icon: Package },
    { to: '/inventory', label: 'Inventory & Stock', icon: Boxes },
    { to: '/movements', label: 'Movement Ledger', icon: History },
    { to: '/purchasing', label: 'Purchasing (PO)', icon: ShoppingBag },
    { to: '/sales', label: 'Sales Orders (SO)', icon: TrendingUp },
    { to: '/reports', label: 'Reports & Analytics', icon: BarChart3 },
    { to: '/audit', label: 'Audit Trail', icon: ShieldCheck },
    { to: '/locations', label: 'Warehouses', icon: Building2 },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">BP</div>
          <div className="sidebar-logo-text">
            <span>BizPilot</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500, letterSpacing: '0.05em' }}>
              ENTERPRISE ERP
            </span>
          </div>
        </div>

        {/* Warehouse Selector in Sidebar */}
        <div style={{ marginTop: 'var(--spacing-md)', padding: 'var(--spacing-sm) 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
            <WarehouseIcon size={13} />
            <span>ACTIVE WAREHOUSE</span>
          </div>
          <select
            className="form-control"
            style={{ padding: '6px 10px', fontSize: '0.8rem', background: 'var(--bg-card)' }}
            value={activeWarehouse?.id || ''}
            onChange={(e) => {
              const selected = warehouses.find((w) => w.id === e.target.value);
              if (selected) setActiveWarehouse(selected);
            }}
          >
            {warehouses.map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.code} - {wh.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'var(--accent-primary)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '0.85rem',
              }}
            >
              {user?.first_name ? user.first_name[0] : 'U'}
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                {user?.first_name || 'Admin'} {user?.last_name || ''}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--accent-secondary)' }}>
                {user?.role || 'STAFF'}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="btn btn-outline"
            style={{ padding: '6px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
            title="Sign Out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};
