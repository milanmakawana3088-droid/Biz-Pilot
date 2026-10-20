import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  DollarSign,
  Package,
  PlusCircle,
  RefreshCw,
  ShoppingBag,
  TrendingUp,
  Warehouse as WhIcon,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { DashboardKPIs, ReplenishmentItem, ValuationItem } from '@/types';

export const Dashboard: React.FC = () => {
  const { activeWarehouse } = useAuth();
  const navigate = useNavigate();

  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [replenishment, setReplenishment] = useState<ReplenishmentItem[]>([]);
  const [valuation, setValuation] = useState<ValuationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const whId = activeWarehouse?.id;
      const [kpisData, replData, valData] = await Promise.all([
        api.reports.getDashboard(whId).catch(() => null),
        api.reports.getReplenishment(whId).catch(() => []),
        api.reports.getValuation(whId).catch(() => []),
      ]);
      setKpis(kpisData);
      setReplenishment(replData || []);
      setValuation(valData || []);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeWarehouse]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount || 0);
  };

  return (
    <div>
      {/* Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
        <div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Viewing metrics for:{' '}
            <strong style={{ color: 'var(--accent-secondary)' }}>
              {activeWarehouse ? `${activeWarehouse.code} - ${activeWarehouse.name}` : 'All Warehouses (Global)'}
            </strong>
          </span>
        </div>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button onClick={loadData} className="btn btn-outline" title="Refresh metrics">
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Sync Live</span>
          </button>
          <button onClick={() => navigate('/purchasing')} className="btn btn-primary">
            <PlusCircle size={14} />
            <span>New Purchase Order</span>
          </button>
          <button onClick={() => navigate('/sales')} className="btn btn-outline">
            <PlusCircle size={14} />
            <span>New Sales Order</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="stat-cards-grid">
        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Total Inventory Valuation</span>
            <div className="stat-card-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--status-success)' }}>
              <DollarSign size={20} />
            </div>
          </div>
          <div className="stat-card-value">
            {formatCurrency(kpis?.total_valuation ?? 0)}
          </div>
          <div className="stat-card-trend">
            <span>Asset value across {kpis?.total_warehouses ?? 0} facilities</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Catalog Products</span>
            <div className="stat-card-icon" style={{ background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-primary)' }}>
              <Package size={20} />
            </div>
          </div>
          <div className="stat-card-value">{kpis?.total_products ?? 0}</div>
          <div className="stat-card-trend">
            <span>Active SKUs registered</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Low Stock Alerts</span>
            <div
              className="stat-card-icon"
              style={{
                background: (kpis?.low_stock_count ?? 0) > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                color: (kpis?.low_stock_count ?? 0) > 0 ? 'var(--status-danger)' : 'var(--status-success)',
              }}
            >
              <AlertTriangle size={20} />
            </div>
          </div>
          <div
            className="stat-card-value"
            style={{ color: (kpis?.low_stock_count ?? 0) > 0 ? 'var(--status-danger)' : 'var(--text-main)' }}
          >
            {kpis?.low_stock_count ?? 0}
          </div>
          <div className="stat-card-trend">
            <span>Items below safety/reorder point</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Open Purchase Orders</span>
            <div className="stat-card-icon" style={{ background: 'rgba(14, 165, 233, 0.1)', color: 'var(--accent-secondary)' }}>
              <ShoppingBag size={20} />
            </div>
          </div>
          <div className="stat-card-value">{kpis?.open_pos_count ?? 0}</div>
          <div className="stat-card-trend">
            <span>Pending or partial goods receipt</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Open Sales Orders</span>
            <div className="stat-card-icon" style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--status-warning)' }}>
              <TrendingUp size={20} />
            </div>
          </div>
          <div className="stat-card-value">{kpis?.open_sos_count ?? 0}</div>
          <div className="stat-card-trend">
            <span>Confirmed or pending shipment</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-header">
            <span className="stat-card-label">Active Warehouses</span>
            <div className="stat-card-icon" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#a78bfa' }}>
              <WhIcon size={20} />
            </div>
          </div>
          <div className="stat-card-value">{kpis?.total_warehouses ?? 0}</div>
          <div className="stat-card-trend">
            <span>Multi-facility distribution network</span>
          </div>
        </div>
      </div>

      {/* Two Column Grid: Low Stock Alert Table & Valuation Table */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 'var(--spacing-lg)', marginTop: 'var(--spacing-lg)' }}>
        {/* Critical Replenishment Deficit */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                Critical Stock Deficit Alerts
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Products where Available Stock &lt; Reorder Point
              </p>
            </div>
            <button onClick={() => navigate('/reports')} className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '6px 10px' }}>
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {replenishment.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              All inventory levels are currently above reorder thresholds. No immediate shortages.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Warehouse</th>
                    <th>Available</th>
                    <th>Reorder Pt</th>
                    <th>Shortage</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {replenishment.slice(0, 5).map((item) => (
                    <tr key={`${item.warehouse_id}-${item.product_id}`}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.product_name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.sku}</div>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{item.warehouse_name}</span>
                      </td>
                      <td>
                        <span style={{ color: 'var(--status-danger)', fontWeight: 600 }}>{item.available}</span>
                      </td>
                      <td>{item.reorder_point}</td>
                      <td>
                        <span className="badge badge-danger">-{item.shortage_quantity}</span>
                      </td>
                      <td>
                        <button
                          onClick={() => navigate('/purchasing')}
                          className="btn btn-outline"
                          style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                        >
                          Order {item.suggested_order_quantity}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Top Valuation Items */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-md)' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
                High-Value Stock Assets
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Largest carrying value products in inventory
              </p>
            </div>
            <button onClick={() => navigate('/inventory')} className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '6px 10px' }}>
              <span>View Stock</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {valuation.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No inventory records currently found.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>SKU & Product</th>
                    <th>On Hand</th>
                    <th>Unit Cost</th>
                    <th>Total Value</th>
                  </tr>
                </thead>
                <tbody>
                  {valuation.slice(0, 5).map((item) => (
                    <tr key={`${item.warehouse_id}-${item.product_id}`}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.product_name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.sku}</div>
                      </td>
                      <td>
                        <strong>{item.on_hand}</strong>
                      </td>
                      <td>{formatCurrency(item.unit_cost)}</td>
                      <td>
                        <strong style={{ color: 'var(--status-success)' }}>
                          {formatCurrency(item.total_valuation)}
                        </strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
