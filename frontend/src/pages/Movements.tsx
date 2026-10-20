import React, { useEffect, useState } from 'react';
import { Download, Filter, History, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { MovementType, StockMovement } from '@/types';

export const Movements: React.FC = () => {
  const { activeWarehouse, warehouses } = useAuth();
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (activeWarehouse) {
      setSelectedWarehouseId(activeWarehouse.id);
    }
  }, [activeWarehouse]);

  const loadMovements = async () => {
    setIsLoading(true);
    try {
      const res = await api.inventory.getMovements({
        warehouse_id: selectedWarehouseId || undefined,
        movement_type: selectedType || undefined,
        size: 150,
      });
      setMovements(res.items || []);
    } catch (err) {
      console.error('Failed to load stock movements ledger', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMovements();
  }, [selectedWarehouseId, selectedType]);

  const getMovementBadge = (type: MovementType) => {
    switch (type) {
      case 'PURCHASE_RECEIPT':
        return <span className="badge badge-success">GRN Receipt</span>;
      case 'SALES_SHIPMENT':
        return <span className="badge badge-primary">Sales Dispatch</span>;
      case 'TRANSFER_IN':
        return <span className="badge badge-info">Transfer IN</span>;
      case 'TRANSFER_OUT':
        return <span className="badge badge-warning">Transfer OUT</span>;
      case 'ADJUSTMENT_IN':
        return <span className="badge badge-info">Adjustment (+)</span>;
      case 'ADJUSTMENT_OUT':
        return <span className="badge badge-danger">Adjustment (-)</span>;
      default:
        return <span className="badge badge-neutral">{type}</span>;
    }
  };

  const filteredMovements = movements.filter((m) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      m.product?.sku.toLowerCase().includes(term) ||
      m.product?.name.toLowerCase().includes(term) ||
      m.reference_id?.toLowerCase().includes(term) ||
      m.reason_code?.toLowerCase().includes(term)
    );
  });

  const formatDate = (iso: string) => {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div>
      {/* Integrity banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          marginBottom: 'var(--spacing-lg)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={20} color="var(--accent-primary)" />
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Append-Only Dual-Write Movement Ledger
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              All inventory balance mutations require dual-write transaction entry. Ledger rows are cryptographically immutable.
            </div>
          </div>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Total Audit Records: <strong>{filteredMovements.length}</strong>
        </div>
      </div>

      {/* Filter controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flex: 1, maxWidth: '650px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by SKU, Reference ID (PO/SO/TR), or reason..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <select
            className="form-control"
            style={{ width: '200px' }}
            value={selectedWarehouseId}
            onChange={(e) => setSelectedWarehouseId(e.target.value)}
          >
            <option value="">All Warehouses</option>
            {warehouses.map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.code} - {wh.name}
              </option>
            ))}
          </select>

          <select
            className="form-control"
            style={{ width: '180px' }}
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="PURCHASE_RECEIPT">Goods Receipt (GRN)</option>
            <option value="SALES_SHIPMENT">Sales Shipment</option>
            <option value="TRANSFER_IN">Transfer IN</option>
            <option value="TRANSFER_OUT">Transfer OUT</option>
            <option value="ADJUSTMENT_IN">Adjustment (+)</option>
            <option value="ADJUSTMENT_OUT">Adjustment (-)</option>
          </select>
        </div>

        <button onClick={loadMovements} className="btn btn-outline" title="Refresh">
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          <span>Sync Ledger</span>
        </button>
      </div>

      {/* Movement Ledger Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Type</th>
                <th>Warehouse</th>
                <th>Product SKU & Name</th>
                <th>Delta Qty</th>
                <th>Before &rarr; After</th>
                <th>Unit Cost</th>
                <th>Reference Doc</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {filteredMovements.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Querying movement ledger...' : 'No ledger movements recorded for this filter.'}
                  </td>
                </tr>
              ) : (
                filteredMovements.map((m) => {
                  const isPositive = m.quantity > 0;
                  return (
                    <tr key={m.id}>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {formatDate(m.created_at)}
                      </td>
                      <td>{getMovementBadge(m.movement_type)}</td>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.85rem' }}>
                          {m.warehouse?.code || m.warehouse_id}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                          {m.product?.name || `Product #${m.product_id}`}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)' }}>
                          {m.product?.sku}
                        </div>
                      </td>
                      <td>
                        <span
                          style={{
                            fontWeight: 700,
                            color: isPositive ? 'var(--status-success)' : 'var(--status-danger)',
                          }}
                        >
                          {isPositive ? `+${m.quantity}` : m.quantity}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{m.balance_before}</span>
                        <span style={{ margin: '0 6px', color: 'var(--text-muted)' }}>&rarr;</span>
                        <strong style={{ color: 'var(--text-main)' }}>{m.balance_after}</strong>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>${Number(m.unit_cost || 0).toFixed(2)}</td>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-main)' }}>
                          {m.reference_id || m.reference_type}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {m.reason_code || '-'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
