import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Eye,
  FileCheck,
  PackageCheck,
  Plus,
  RefreshCw,
  Search,
  ShoppingBag,
  Trash2,
  Truck,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  POStatus,
  Product,
  PurchaseOrder,
  PurchaseOrderItem,
  Supplier,
  Warehouse,
} from '@/types';

export const Purchasing: React.FC = () => {
  const { activeWarehouse, warehouses } = useAuth();
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedWhId, setSelectedWhId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null);
  const [isReceiptOpen, setIsReceiptOpen] = useState(false);

  // New PO form state
  const [poForm, setPoForm] = useState({
    supplier_id: '',
    warehouse_id: '',
    expected_delivery_date: '',
    notes: '',
    items: [{ product_id: '', quantity_ordered: 10, unit_price: 0 }],
  });

  // GRN Receipt form state
  const [receiptForm, setReceiptForm] = useState<{
    items: { item_id: string; product_name: string; remaining: number; quantity_received: number }[];
    notes: string;
  }>({ items: [], notes: '' });

  useEffect(() => {
    if (activeWarehouse) {
      setSelectedWhId(activeWarehouse.id);
    }
  }, [activeWarehouse]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [poRes, supRes, prodRes] = await Promise.all([
        api.purchasing.listOrders({
          warehouse_id: selectedWhId || undefined,
          status: selectedStatus || undefined,
          size: 100,
        }),
        api.suppliers.list().catch(() => []),
        api.products.list({ size: 200 }).catch(() => ({ items: [] })),
      ]);
      setOrders(poRes.items || []);
      setSuppliers(supRes || []);
      setProducts(prodRes.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load purchase orders');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedWhId, selectedStatus]);

  const handleOpenCreate = () => {
    const firstWh = selectedWhId || warehouses[0]?.id || '';
    const firstSup = suppliers[0]?.id || '';
    const firstProd = products[0];

    setPoForm({
      supplier_id: firstSup,
      warehouse_id: firstWh,
      expected_delivery_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      notes: '',
      items: [
        {
          product_id: firstProd?.id || '',
          quantity_ordered: 50,
          unit_price: firstProd ? Number(firstProd.cost_price) : 0,
        },
      ],
    });
    setIsCreateOpen(true);
  };

  const addItemToPO = () => {
    const firstProd = products[0];
    setPoForm({
      ...poForm,
      items: [
        ...poForm.items,
        {
          product_id: firstProd?.id || '',
          quantity_ordered: 20,
          unit_price: firstProd ? Number(firstProd.cost_price) : 0,
        },
      ],
    });
  };

  const removeItemFromPO = (index: number) => {
    setPoForm({
      ...poForm,
      items: poForm.items.filter((_, i) => i !== index),
    });
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    try {
      await api.purchasing.createOrder({
        supplier_id: poForm.supplier_id,
        warehouse_id: poForm.warehouse_id,
        expected_delivery_date: poForm.expected_delivery_date || undefined,
        notes: poForm.notes,
        items: poForm.items.map((item) => ({
          product_id: item.product_id,
          quantity_ordered: Number(item.quantity_ordered),
          unit_price: Number(item.unit_price),
        })),
      });
      setSuccessMsg('Purchase Order created successfully in DRAFT state.');
      setIsCreateOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to create purchase order');
    }
  };

  const handleApprovePO = async (poId: string) => {
    setError(null);
    try {
      await api.purchasing.approveOrder(poId);
      setSuccessMsg(`PO #${poId} approved for receiving.`);
      loadData();
      if (selectedOrder) {
        const updated = await api.purchasing.getOrder(poId);
        setSelectedOrder(updated);
      }
    } catch (err: any) {
      setError(err.message || 'Approval failed');
    }
  };

  const handleOpenReceipt = (po: PurchaseOrder) => {
    setSelectedOrder(po);
    const receiptItems = po.items.map((item) => {
      const remaining = item.quantity_ordered - item.quantity_received;
      return {
        item_id: item.id,
        product_name: item.product?.name || `Product #${item.product_id}`,
        remaining: Math.max(0, remaining),
        quantity_received: Math.max(0, remaining), // default to remaining
      };
    });
    setReceiptForm({ items: receiptItems, notes: 'Standard dock goods receipt' });
    setIsReceiptOpen(true);
  };

  const handleReceiptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setError(null);
    setSuccessMsg(null);

    const activeItems = receiptForm.items.filter((it) => it.quantity_received > 0);
    if (activeItems.length === 0) {
      setError('Please specify a received quantity greater than 0 for at least one item');
      return;
    }

    try {
      await api.purchasing.receiveGoods(selectedOrder.id, {
        warehouse_id: selectedOrder.warehouse_id,
        notes: receiptForm.notes,
        items: activeItems.map((it) => ({
          item_id: it.item_id,
          quantity_received: Number(it.quantity_received),
        })),
      });
      setSuccessMsg(`Goods receipt note (GRN) generated! On-hand inventory increased with dual-write ledger entries.`);
      setIsReceiptOpen(false);
      setSelectedOrder(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Goods receipt failed');
    }
  };

  const getStatusBadge = (status: POStatus) => {
    switch (status) {
      case 'DRAFT':
        return <span className="badge badge-neutral">Draft</span>;
      case 'APPROVED':
        return <span className="badge badge-info">Approved</span>;
      case 'PARTIAL':
        return <span className="badge badge-warning">Partial GRN</span>;
      case 'RECEIVED':
        return <span className="badge badge-success">Fully Received</span>;
      case 'CANCELLED':
        return <span className="badge badge-danger">Cancelled</span>;
      default:
        return <span className="badge badge-neutral">{status}</span>;
    }
  };

  return (
    <div>
      {/* Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flex: 1, maxWidth: '650px' }}>
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

          <select
            className="form-control"
            style={{ width: '180px' }}
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="APPROVED">Approved</option>
            <option value="PARTIAL">Partial Receipt</option>
            <option value="RECEIVED">Received</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Sync</span>
          </button>
          <button onClick={handleOpenCreate} className="btn btn-primary">
            <Plus size={16} />
            <span>Create Purchase Order</span>
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

      {/* PO List Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Supplier</th>
                <th>Warehouse</th>
                <th>Order Date</th>
                <th>Total Value</th>
                <th>Items Progress</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Workflow Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Querying purchase orders...' : 'No purchase orders found.'}
                  </td>
                </tr>
              ) : (
                orders.map((po) => {
                  const totalOrdered = po.items?.reduce((s, it) => s + it.quantity_ordered, 0) || 0;
                  const totalReceived = po.items?.reduce((s, it) => s + it.quantity_received, 0) || 0;

                  return (
                    <tr key={po.id}>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'monospace' }}>
                          {po.order_number}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{po.supplier?.name || 'Supplier'}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{po.supplier?.code}</div>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{po.warehouse?.code}</span>
                      </td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        {po.order_date ? new Date(po.order_date).toLocaleDateString() : '-'}
                      </td>
                      <td>
                        <strong>${Number(po.total_amount).toFixed(2)}</strong>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.8rem', marginBottom: '2px' }}>
                          <span>{totalReceived}</span> / <span>{totalOrdered}</span> units
                        </div>
                        <div
                          style={{
                            width: '100px',
                            height: '5px',
                            background: 'var(--bg-card-hover)',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: totalOrdered > 0 ? `${(totalReceived / totalOrdered) * 100}%` : '0%',
                              height: '100%',
                              background: totalReceived === totalOrdered ? 'var(--status-success)' : 'var(--accent-secondary)',
                            }}
                          />
                        </div>
                      </td>
                      <td>{getStatusBadge(po.status)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          {po.status === 'DRAFT' && (
                            <button
                              onClick={() => handleApprovePO(po.id)}
                              className="btn btn-primary"
                              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            >
                              <FileCheck size={13} />
                              <span>Approve</span>
                            </button>
                          )}

                          {(po.status === 'APPROVED' || po.status === 'PARTIAL') && (
                            <button
                              onClick={() => handleOpenReceipt(po)}
                              className="btn btn-primary"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', background: 'var(--status-success)', borderColor: 'var(--status-success)' }}
                            >
                              <PackageCheck size={13} />
                              <span>Receive Goods</span>
                            </button>
                          )}

                          <button
                            onClick={() => setSelectedOrder(po)}
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            title="View PO Details"
                          >
                            <Eye size={13} />
                            <span>Details</span>
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

      {/* Create PO Modal */}
      {isCreateOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '720px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Create Purchase Order</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Supplier *</label>
                  <select
                    className="form-control"
                    required
                    value={poForm.supplier_id}
                    onChange={(e) => setPoForm({ ...poForm, supplier_id: e.target.value })}
                  >
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.code} - {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Receiving Warehouse *</label>
                  <select
                    className="form-control"
                    required
                    value={poForm.warehouse_id}
                    onChange={(e) => setPoForm({ ...poForm, warehouse_id: e.target.value })}
                  >
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.code} - {w.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Expected Delivery Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={poForm.expected_delivery_date}
                  onChange={(e) => setPoForm({ ...poForm, expected_delivery_date: e.target.value })}
                />
              </div>

              {/* Order Items */}
              <div style={{ marginTop: 'var(--spacing-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>Line Items Ordered *</label>
                  <button type="button" onClick={addItemToPO} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.75rem' }}>
                    <Plus size={13} />
                    <span>Add Item</span>
                  </button>
                </div>

                {poForm.items.map((item, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 'var(--spacing-sm)', alignItems: 'center', marginBottom: '8px' }}>
                    <select
                      className="form-control"
                      required
                      value={item.product_id}
                      onChange={(e) => {
                        const prod = products.find((p) => p.id === e.target.value);
                        const updated = [...poForm.items];
                        updated[idx].product_id = e.target.value;
                        if (prod) updated[idx].unit_price = Number(prod.cost_price);
                        setPoForm({ ...poForm, items: updated });
                      }}
                    >
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.sku} - {p.name}
                        </option>
                      ))}
                    </select>

                    <input
                      type="number"
                      min="1"
                      required
                      className="form-control"
                      placeholder="Qty"
                      value={item.quantity_ordered}
                      onChange={(e) => {
                        const updated = [...poForm.items];
                        updated[idx].quantity_ordered = parseInt(e.target.value) || 1;
                        setPoForm({ ...poForm, items: updated });
                      }}
                    />

                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      required
                      className="form-control"
                      placeholder="Unit Price"
                      value={item.unit_price}
                      onChange={(e) => {
                        const updated = [...poForm.items];
                        updated[idx].unit_price = parseFloat(e.target.value) || 0;
                        setPoForm({ ...poForm, items: updated });
                      }}
                    />

                    {poForm.items.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeItemFromPO(idx)}
                        className="btn btn-outline"
                        style={{ padding: '6px', color: 'var(--status-danger)' }}
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="form-group" style={{ marginTop: 'var(--spacing-md)' }}>
                <label className="form-label">Order Notes / Supplier Terms</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={poForm.notes}
                  onChange={(e) => setPoForm({ ...poForm, notes: e.target.value })}
                />
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsCreateOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Submit Purchase Order
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Goods Receipt (GRN) Modal */}
      {isReceiptOpen && selectedOrder && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Receive Goods (GRN) for {selectedOrder.order_number}</h3>
              <button
                onClick={() => setIsReceiptOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleReceiptSubmit}>
              <div style={{ marginBottom: 'var(--spacing-md)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Receiving into: <strong style={{ color: 'var(--text-main)' }}>{selectedOrder.warehouse?.name}</strong>. Enter quantities physically inspected and verified at dock.
              </div>

              <div className="table-responsive" style={{ marginBottom: 'var(--spacing-md)' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Remaining Qty</th>
                      <th>Qty Received Today</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receiptForm.items.map((item, idx) => (
                      <tr key={item.item_id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{item.product_name}</div>
                        </td>
                        <td>{item.remaining}</td>
                        <td style={{ width: '150px' }}>
                          <input
                            type="number"
                            min="0"
                            max={item.remaining}
                            className="form-control"
                            value={item.quantity_received}
                            onChange={(e) => {
                              const updated = [...receiptForm.items];
                              updated[idx].quantity_received = parseInt(e.target.value) || 0;
                              setReceiptForm({ ...receiptForm, items: updated });
                            }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="form-group">
                <label className="form-label">Receiving Notes / Bill of Lading</label>
                <input
                  type="text"
                  className="form-control"
                  value={receiptForm.notes}
                  onChange={(e) => setReceiptForm({ ...receiptForm, notes: e.target.value })}
                />
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsReceiptOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ background: 'var(--status-success)', borderColor: 'var(--status-success)' }}>
                  Confirm Goods Receipt
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PO Detail View Modal */}
      {selectedOrder && !isReceiptOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">{selectedOrder.order_number}</h3>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Supplier: {selectedOrder.supplier?.name} &bull; Warehouse: {selectedOrder.warehouse?.name}
                </div>
              </div>
              <button
                onClick={() => setSelectedOrder(null)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ marginBottom: 'var(--spacing-md)', display: 'flex', gap: 'var(--spacing-md)' }}>
              <div>Status: {getStatusBadge(selectedOrder.status)}</div>
              <div>Total: <strong>${Number(selectedOrder.total_amount).toFixed(2)}</strong></div>
            </div>

            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Ordered</th>
                    <th>Received</th>
                    <th>Unit Price</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedOrder.items.map((it) => (
                    <tr key={it.id}>
                      <td>{it.product?.name || it.product_id}</td>
                      <td>{it.quantity_ordered}</td>
                      <td>{it.quantity_received}</td>
                      <td>${Number(it.unit_price).toFixed(2)}</td>
                      <td>${Number(it.line_total).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
              <button onClick={() => setSelectedOrder(null)} className="btn btn-outline">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
