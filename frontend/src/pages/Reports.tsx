import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  DollarSign,
  Download,
  Filter,
  Package,
  RefreshCw,
  ShoppingBag,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { ReplenishmentItem, ValuationItem } from '@/types';

export const Reports: React.FC = () => {
  const { activeWarehouse, warehouses } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'VALUATION' | 'REPLENISHMENT'>('VALUATION');
  const [selectedWhId, setSelectedWhId] = useState<string>('');
  const [valuationData, setValuationData] = useState<ValuationItem[]>([]);
  const [replenishmentData, setReplenishmentData] = useState<ReplenishmentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (activeWarehouse) {
      setSelectedWhId(activeWarehouse.id);
    }
  }, [activeWarehouse]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'VALUATION') {
        const val = await api.reports.getValuation(selectedWhId || undefined);
        setValuationData(val || []);
      } else {
        const repl = await api.reports.getReplenishment(selectedWhId || undefined);
        setReplenishmentData(repl || []);
      }
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab, selectedWhId]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount || 0);
  };

  const totalValuation = valuationData.reduce((s, it) => s + Number(it.total_valuation || 0), 0);
  const totalUnits = valuationData.reduce((s, it) => s + Number(it.on_hand || 0), 0);

  return (
    <div>
      {/* Controls & Tab Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('VALUATION')}
            className={`btn ${activeTab === 'VALUATION' ? 'btn-primary' : 'btn-outline'}`}
          >
            <DollarSign size={15} />
            <span>Inventory Valuation Report</span>
          </button>
          <button
            onClick={() => setActiveTab('REPLENISHMENT')}
            className={`btn ${activeTab === 'REPLENISHMENT' ? 'btn-primary' : 'btn-outline'}`}
          >
            <AlertTriangle size={15} />
            <span>Replenishment & Deficit Analysis</span>
          </button>
        </div>

        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <select
            className="form-control"
            style={{ width: '220px' }}
            value={selectedWhId}
            onChange={(e) => setSelectedWhId(e.target.value)}
          >
            <option value="">All Warehouses</option>
            {warehouses.map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.code} - {wh.name}
              </option>
            ))}
          </select>

          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {activeTab === 'VALUATION' ? (
        <div>
          {/* Summary KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
            <div className="card">
              <span className="stat-card-label">Total Portfolio Asset Value</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--status-success)', marginTop: '4px' }}>
                {formatCurrency(totalValuation)}
              </div>
            </div>
            <div className="card">
              <span className="stat-card-label">Physical Units in Stock</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px' }}>
                {totalUnits.toLocaleString()} units
              </div>
            </div>
            <div className="card">
              <span className="stat-card-label">Catalog SKUs Evaluated</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '4px' }}>
                {valuationData.length} SKUs
              </div>
            </div>
          </div>

          {/* Valuation Table */}
          <div className="card" style={{ padding: 0 }}>
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Warehouse</th>
                    <th>SKU & Product Name</th>
                    <th>On-Hand</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Unit Cost</th>
                    <th>Carrying Valuation</th>
                  </tr>
                </thead>
                <tbody>
                  {valuationData.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                        {isLoading ? 'Calculating asset carrying values...' : 'No valuation records found.'}
                      </td>
                    </tr>
                  ) : (
                    valuationData.map((it) => (
                      <tr key={`${it.warehouse_id}-${it.product_id}`}>
                        <td>
                          <span className="badge badge-info">{it.warehouse_name}</span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{it.product_name}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)' }}>{it.sku}</div>
                        </td>
                        <td>
                          <strong>{it.on_hand}</strong>
                        </td>
                        <td style={{ color: it.reserved > 0 ? 'var(--status-warning)' : 'var(--text-muted)' }}>
                          {it.reserved}
                        </td>
                        <td>
                          <strong style={{ color: 'var(--status-success)' }}>{it.available}</strong>
                        </td>
                        <td>{formatCurrency(it.unit_cost)}</td>
                        <td>
                          <strong style={{ color: 'var(--status-success)', fontSize: '0.95rem' }}>
                            {formatCurrency(it.total_valuation)}
                          </strong>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div>
          {/* Replenishment Deficit Table */}
          <div className="card" style={{ padding: 0 }}>
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Warehouse</th>
                    <th>Product</th>
                    <th>Available</th>
                    <th>Reorder Point</th>
                    <th>Safety Stock</th>
                    <th>Shortage Deficit</th>
                    <th>Suggested Order</th>
                    <th style={{ textAlign: 'right' }}>Procurement Action</th>
                  </tr>
                </thead>
                <tbody>
                  {replenishmentData.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                        {isLoading ? 'Computing reorder thresholds...' : 'No replenishment shortages detected. All inventory levels healthy!'}
                      </td>
                    </tr>
                  ) : (
                    replenishmentData.map((it) => (
                      <tr key={`${it.warehouse_id}-${it.product_id}`}>
                        <td>
                          <span className="badge badge-neutral">{it.warehouse_name}</span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{it.product_name}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{it.sku}</div>
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, color: 'var(--status-danger)' }}>{it.available}</span>
                        </td>
                        <td>{it.reorder_point}</td>
                        <td>{it.safety_stock}</td>
                        <td>
                          <span className="badge badge-danger">-{it.shortage_quantity} units</span>
                        </td>
                        <td>
                          <strong style={{ color: 'var(--status-warning)' }}>
                            +{it.suggested_order_quantity} units
                          </strong>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => navigate('/purchasing')}
                            className="btn btn-primary"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          >
                            <ShoppingBag size={13} />
                            <span>Create PO</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
