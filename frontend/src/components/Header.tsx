import React from 'react';
import { useLocation } from 'react-router-dom';
import { Activity, Bell, Warehouse as WhIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Executive Overview', subtitle: 'Real-time operational KPIs and inventory analytics' },
  '/products': { title: 'Product Catalog', subtitle: 'Manage SKUs, barcodes, pricing, and category hierarchies' },
  '/inventory': { title: 'Multi-Warehouse Stock', subtitle: 'On-hand, reserved, and available stock levels with atomic adjustments' },
  '/movements': { title: 'Stock Movement Ledger', subtitle: 'Append-only audit trail of dual-write inventory transactions' },
  '/purchasing': { title: 'Purchase Orders', subtitle: 'Supplier procurement, PO approval, and partial goods receipts' },
  '/sales': { title: 'Sales Orders', subtitle: 'Customer orders, atomic stock reservations, and shipments' },
  '/reports': { title: 'Valuation & Replenishment', subtitle: 'Inventory carrying cost and reorder point deficit analytics' },
  '/audit': { title: 'Audit Trail', subtitle: 'Comprehensive change history across all business entities' },
  '/locations': { title: 'Warehouses & Locations', subtitle: 'Multi-facility topology and storage location settings' },
};

export const Header: React.FC = () => {
  const location = useLocation();
  const { activeWarehouse, user } = useAuth();
  const info = routeTitles[location.pathname] || {
    title: 'BizPilot ERP',
    subtitle: 'Enterprise Inventory Management System',
  };

  return (
    <header className="header">
      <div>
        <h1 className="header-title">{info.title}</h1>
        <p className="header-subtitle">{info.subtitle}</p>
      </div>

      <div className="header-actions">
        {activeWarehouse && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8rem',
              color: 'var(--text-main)',
            }}
          >
            <WhIcon size={14} color="var(--accent-secondary)" />
            <span style={{ fontWeight: 600 }}>{activeWarehouse.code}</span>
            <span style={{ color: 'var(--text-muted)' }}>({activeWarehouse.name})</span>
          </div>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            padding: '6px 10px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(16, 185, 129, 0.1)',
            color: 'var(--status-success)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'var(--status-success)',
              display: 'inline-block',
            }}
          />
          <Activity size={12} />
          <span>PostgreSQL Active</span>
        </div>

        <button
          className="btn btn-outline"
          style={{ padding: '8px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
          title="Notifications"
        >
          <Bell size={18} />
        </button>
      </div>
    </header>
  );
};
