import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowRightLeft,
  Boxes,
  CheckCircle2,
  Filter,
  Sliders,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { Product, StockLevel, Warehouse } from '@/types';

export const Inventory: React.FC = () => {
  const { activeWarehouse, warehouses } = useAuth();
  const [stockLevels, setStockLevels] = useState<StockLevel[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>('');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Adjustment Modal State
  const [isAdjustmentOpen, setIsAdjustmentOpen] = useState(false);
  const [adjData, setAdjData] = useState({
    warehouse_id: '',
    product_id: '',
    type: 'IN' as 'IN' | 'OUT',
    quantity: 1,
    unit_cost: 0,
    reason_code: 'CYCLE_COUNT',
  });

  // Transfer Modal State
  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [transferData, setTransferData] = useState({
    source_warehouse_id: '',
    destination_warehouse_id: '',
    product_id: '',
    quantity: 1,
    reason_code: 'STOCK_REBALANCE',
  });

  useEffect(() => {
    if (activeWarehouse) {
      setSelectedWarehouseId(activeWarehouse.id);
    }
  }, [activeWarehouse]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [levelsRes, prodRes] = await Promise.all([
        api.inventory.getStockLevels({
          warehouse_id: selectedWarehouseId || undefined,
          size: 100,
        }),
        api.products.list({ size: 200 }),
      ]);
      setStockLevels(levelsRes.items || []);
      setProducts(prodRes.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load inventory stock levels');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedWarehouseId]);

  const handleOpenAdjustment = (level?: StockLevel) => {
    setAdjData({
      warehouse_id: level ? level.warehouse_id : selectedWarehouseId || warehouses[0]?.id || '',
      product_id: level ? level.product_id : products[0]?.id || '',
      type: 'IN',
      quantity: 10,
      unit_cost: level?.product ? Number(level.product.cost_price) : 0,
      reason_code: 'CYCLE_COUNT',
    });
    setIsAdjustmentOpen(true);
  };

  const handleOpenTransfer = (level?: StockLevel) => {
    const srcId = level ? level.warehouse_id : selectedWarehouseId || warehouses[0]?.id || '';
    const otherWh = warehouses.find((w) => w.id !== srcId);

    setTransferData({
      source_warehouse_id: srcId,
      destination_warehouse_id: otherWh ? otherWh.id : '',
      product_id: level ? level.product_id : products[0]?.id || '',
      quantity: 5,
      reason_code: 'STOCK_REBALANCE',
    });
    setIsTransferOpen(true);
  };

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    try {
      await api.inventory.adjustStock({
        warehouse_id: adjData.warehouse_id,
        product_id: adjData.product_id,
        type: adjData.type,
        quantity: Number(adjData.quantity),
        unit_cost: Number(adjData.unit_cost) || undefined,
        reason_code: adjData.reason_code,
      });
      setSuccessMsg(`Stock adjustment (${adjData.type} ${adjData.quantity}) completed successfully! Dual movement recorded.`);
      setIsAdjustmentOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Stock adjustment failed');
    }
  };

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    if (transferData.source_warehouse_id === transferData.destination_warehouse_id) {
      setError('Source and Destination warehouses must be different');
      return;
    }
    try {
      await api.inventory.transferStock({
        source_warehouse_id: transferData.source_warehouse_id,
        destination_warehouse_id: transferData.destination_warehouse_id,
        product_id: transferData.product_id,
        quantity: Number(transferData.quantity),
        reason_code: transferData.reason_code,
      });
      setSuccessMsg(`Inter-warehouse transfer of ${transferData.quantity} units successfully executed! Both warehouses updated atomically.`);
      setIsTransferOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Stock transfer failed');
    }
  };

  const filteredLevels = stockLevels.filter((lvl) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      lvl.product?.name.toLowerCase().includes(term) ||
      lvl.product?.sku.toLowerCase().includes(term) ||
      lvl.warehouse?.name.toLowerCase().includes(term)
    );
  });

  return (
    <div>
      {/* Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flex: 1, maxWidth: '650px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '36px' }}
              placeholder="Search stock by SKU, product name, or warehouse..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <select
            className="form-control"
            style={{ width: '220px' }}
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
        </div>

        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Sync</span>
          </button>
          <button onClick={() => handleOpenAdjustment()} className="btn btn-primary">
            <Sliders size={15} />
            <span>Stock Adjustment</span>
          </button>
          <button onClick={() => handleOpenTransfer()} className="btn btn-outline">
            <ArrowRightLeft size={15} />
            <span>Inter-Warehouse Transfer</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--status-danger)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: 'var(--spacing-md)', border: '1px solid rgba(239, 68, 68, 0.3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--status-success)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: 'var(--spacing-md)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Stock Levels Table */}
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
                <th>Reorder Threshold</th>
                <th>Inventory Health</th>
                <th style={{ textAlign: 'right' }}>Quick Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredLevels.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Fetching real-time stock balances...' : 'No inventory records found for selection.'}
                  </td>
                </tr>
              ) : (
                filteredLevels.map((lvl) => {
                  const isLow = lvl.available <= (lvl.product?.reorder_point ?? 0);
                  return (
                    <tr key={lvl.id}>
                      <td>
                        <span className="badge badge-info">{lvl.warehouse?.code || lvl.warehouse_id}</span>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {lvl.warehouse?.name}
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                          {lvl.product?.name || `Product #${lvl.product_id}`}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)' }}>
                          {lvl.product?.sku}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                          {lvl.on_hand}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.9rem', color: lvl.reserved > 0 ? 'var(--status-warning)' : 'var(--text-muted)' }}>
                          {lvl.reserved}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: '1rem',
                            fontWeight: 700,
                            color: isLow ? 'var(--status-danger)' : 'var(--status-success)',
                          }}
                        >
                          {lvl.available}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          {lvl.product?.reorder_point ?? 0}
                        </span>
                      </td>
                      <td>
                        {isLow ? (
                          <span className="badge badge-danger">Below Reorder Pt</span>
                        ) : (
                          <span className="badge badge-success">Sufficient</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleOpenAdjustment(lvl)}
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            title="Adjust Quantity"
                          >
                            <Sliders size={13} />
                            <span>Adjust</span>
                          </button>
                          <button
                            onClick={() => handleOpenTransfer(lvl)}
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            title="Transfer Stock"
                          >
                            <ArrowRightLeft size={13} />
                            <span>Transfer</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stock Adjustment Modal */}
      {isAdjustmentOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Manual Stock Adjustment</h3>
              <button
                onClick={() => setIsAdjustmentOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAdjustSubmit}>
              <div className="form-group">
                <label className="form-label">Target Warehouse *</label>
                <select
                  className="form-control"
                  required
                  value={adjData.warehouse_id}
                  onChange={(e) => setAdjData({ ...adjData, warehouse_id: e.target.value })}
                >
                  {warehouses.map((wh) => (
                    <option key={wh.id} value={wh.id}>
                      {wh.code} - {wh.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Product SKU *</label>
                <select
                  className="form-control"
                  required
                  value={adjData.product_id}
                  onChange={(e) => {
                    const selected = products.find((p) => p.id === e.target.value);
                    setAdjData({
                      ...adjData,
                      product_id: e.target.value,
                      unit_cost: selected ? Number(selected.cost_price) : 0,
                    });
                  }}
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Direction *</label>
                  <select
                    className="form-control"
                    value={adjData.type}
                    onChange={(e) => setAdjData({ ...adjData, type: e.target.value as 'IN' | 'OUT' })}
                  >
                    <option value="IN">Stock IN (Positive Increment)</option>
                    <option value="OUT">Stock OUT (Negative Write-off)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Adjustment Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    className="form-control"
                    value={adjData.quantity}
                    onChange={(e) => setAdjData({ ...adjData, quantity: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Unit Cost ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="form-control"
                    value={adjData.unit_cost}
                    onChange={(e) => setAdjData({ ...adjData, unit_cost: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Reason Code *</label>
                  <select
                    className="form-control"
                    required
                    value={adjData.reason_code}
                    onChange={(e) => setAdjData({ ...adjData, reason_code: e.target.value })}
                  >
                    <option value="CYCLE_COUNT">Cycle Count Verification</option>
                    <option value="DAMAGED">Damaged in Handling</option>
                    <option value="EXPIRED">Expired Shelf Life</option>
                    <option value="THEFT">Shrinkage / Theft</option>
                    <option value="CORRECTION">Data Entry Correction</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsAdjustmentOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Commit Adjustment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inter-Warehouse Transfer Modal */}
      {isTransferOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '540px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Inter-Warehouse Stock Transfer</h3>
              <button
                onClick={() => setIsTransferOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleTransferSubmit}>
              <div className="form-group">
                <label className="form-label">Product to Transfer *</label>
                <select
                  className="form-control"
                  required
                  value={transferData.product_id}
                  onChange={(e) => setTransferData({ ...transferData, product_id: e.target.value })}
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Source Warehouse *</label>
                  <select
                    className="form-control"
                    required
                    value={transferData.source_warehouse_id}
                    onChange={(e) => setTransferData({ ...transferData, source_warehouse_id: e.target.value })}
                  >
                    {warehouses.map((wh) => (
                      <option key={wh.id} value={wh.id}>
                        {wh.code} - {wh.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Destination Warehouse *</label>
                  <select
                    className="form-control"
                    required
                    value={transferData.destination_warehouse_id}
                    onChange={(e) => setTransferData({ ...transferData, destination_warehouse_id: e.target.value })}
                  >
                    {warehouses.map((wh) => (
                      <option key={wh.id} value={wh.id}>
                        {wh.code} - {wh.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Transfer Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    className="form-control"
                    value={transferData.quantity}
                    onChange={(e) => setTransferData({ ...transferData, quantity: parseInt(e.target.value) || 1 })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Reason / Reference Note</label>
                  <input
                    type="text"
                    className="form-control"
                    value={transferData.reason_code}
                    onChange={(e) => setTransferData({ ...transferData, reason_code: e.target.value })}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsTransferOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Execute Atomic Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
