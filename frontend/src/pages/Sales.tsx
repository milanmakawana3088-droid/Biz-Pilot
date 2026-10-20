import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Ban,
  CheckCircle2,
  Eye,
  FileCheck2,
  Plus,
  RefreshCw,
  Search,
  Send,
  Trash2,
  TrendingUp,
  Truck,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  Customer,
  Product,
  SalesOrder,
  SalesOrderItem,
  SOStatus,
  Warehouse,
} from '@/types';

export const Sales: React.FC = () => {
  const { activeWarehouse, warehouses } = useAuth();
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedWhId, setSelectedWhId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<SalesOrder | null>(null);
  const [isShipmentOpen, setIsShipmentOpen] = useState(false);

  // New SO form state
  const [soForm, setSoForm] = useState({
    customer_id: '',
    warehouse_id: '',
    notes: '',
    items: [{ product_id: '', quantity_ordered: 5, unit_price: 0 }],
  });

  // Shipment form state
  const [shipmentForm, setShipmentForm] = useState<{
    carrier: string;
    tracking_number: string;
    notes: string;
    items: { item_id: string; product_name: string; remaining: number; quantity_to_ship: number }[];
  }>({ carrier: 'FedEx Ground', tracking_number: '', notes: '', items: [] });

  useEffect(() => {
    if (activeWarehouse) {
      setSelectedWhId(activeWarehouse.id);
    }
  }, [activeWarehouse]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [soRes, custRes, prodRes] = await Promise.all([
        api.sales.listOrders({
          warehouse_id: selectedWhId || undefined,
          status: selectedStatus || undefined,
          size: 100,
        }),
        api.customers.list().catch(() => []),
        api.products.list({ size: 200 }).catch(() => ({ items: [] })),
      ]);
      setOrders(soRes.items || []);
      setCustomers(custRes || []);
      setProducts(prodRes.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load sales orders');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedWhId, selectedStatus]);

  const handleOpenCreate = () => {
    const firstWh = selectedWhId || warehouses[0]?.id || '';
    const firstCust = customers[0]?.id || '';
    const firstProd = products[0];

    setSoForm({
      customer_id: firstCust,
      warehouse_id: firstWh,
      notes: '',
      items: [
        {
          product_id: firstProd?.id || '',
          quantity_ordered: 5,
          unit_price: firstProd ? Number(firstProd.selling_price) : 0,
        },
      ],
    });
    setIsCreateOpen(true);
  };

  const addItemToSO = () => {
    const firstProd = products[0];
    setSoForm({
      ...soForm,
      items: [
        ...soForm.items,
        {
          product_id: firstProd?.id || '',
          quantity_ordered: 2,
          unit_price: firstProd ? Number(firstProd.selling_price) : 0,
        },
      ],
    });
  };

  const removeItemFromSO = (index: number) => {
    setSoForm({
      ...soForm,
      items: soForm.items.filter((_, i) => i !== index),
    });
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    try {
      await api.sales.createOrder({
        customer_id: soForm.customer_id,
        warehouse_id: soForm.warehouse_id,
        notes: soForm.notes,
        items: soForm.items.map((item) => ({
          product_id: item.product_id,
          quantity_ordered: Number(item.quantity_ordered),
          unit_price: Number(item.unit_price),
        })),
      });
      setSuccessMsg('Sales Order registered in DRAFT status.');
      setIsCreateOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to create sales order');
    }
  };

  const handleConfirmSO = async (soId: string) => {
    setError(null);
    try {
      await api.sales.confirmOrder(soId);
      setSuccessMsg(`Sales Order confirmed! Inventory reserved atomically.`);
      loadData();
      if (selectedOrder) {
        const updated = await api.sales.getOrder(soId);
        setSelectedOrder(updated);
      }
    } catch (err: any) {
      setError(err.message || 'Confirmation & Stock Reservation failed');
    }
  };

  const handleCancelSO = async (soId: string) => {
    if (!window.confirm('Are you sure you want to cancel this order? Any reserved inventory will be freed immediately.')) {
      return;
    }
    setError(null);
    try {
      await api.sales.cancelOrder(soId, 'Customer requested cancellation');
      setSuccessMsg(`Sales Order cancelled. Any reserved stock has been released.`);
      loadData();
      if (selectedOrder) {
        const updated = await api.sales.getOrder(soId);
        setSelectedOrder(updated);
      }
    } catch (err: any) {
      setError(err.message || 'Cancellation failed');
    }
  };

  const handleOpenShipment = (so: SalesOrder) => {
    setSelectedOrder(so);
    const shipmentItems = so.items.map((item) => {
      const remaining = item.quantity_ordered - item.quantity_shipped;
      return {
        item_id: item.id,
        product_name: item.product?.name || `Product #${item.product_id}`,
        remaining: Math.max(0, remaining),
        quantity_to_ship: Math.max(0, remaining),
      };
    });
    setShipmentForm({
      carrier: 'UPS Ground',
      tracking_number: `1Z99999999${Math.floor(10000000 + Math.random() * 90000000)}`,
      notes: 'Customer priority shipment',
      items: shipmentItems,
    });
    setIsShipmentOpen(true);
  };

  const handleShipmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setError(null);
    setSuccessMsg(null);

    const activeItems = shipmentForm.items.filter((it) => it.quantity_to_ship > 0);
    if (activeItems.length === 0) {
      setError('Please specify a shipping quantity greater than 0 for at least one item');
      return;
    }

    try {
      await api.sales.shipGoods(selectedOrder.id, {
        warehouse_id: selectedOrder.warehouse_id,
        carrier: shipmentForm.carrier,
        tracking_number: shipmentForm.tracking_number,
        notes: shipmentForm.notes,
        items: activeItems.map((it) => ({
          item_id: it.item_id,
          quantity_to_ship: Number(it.quantity_to_ship),
        })),
      });
      setSuccessMsg(`Shipment dispatched! On-hand and reserved balances decremented with dual-write ledger movement.`);
      setIsShipmentOpen(false);
      setSelectedOrder(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Shipment dispatch failed');
    }
  };

  const getStatusBadge = (status: SOStatus) => {
    switch (status) {
      case 'DRAFT':
        return <span className="badge badge-neutral">Draft</span>;
      case 'CONFIRMED':
        return <span className="badge badge-info">Stock Reserved</span>;
      case 'PARTIAL':
        return <span className="badge badge-warning">Partial Shipped</span>;
      case 'SHIPPED':
        return <span className="badge badge-success">Fully Shipped</span>;
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
            <option value="CONFIRMED">Stock Reserved</option>
            <option value="PARTIAL">Partial Shipped</option>
            <option value="SHIPPED">Shipped</option>
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
            <span>Create Sales Order</span>
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

      {/* SO List Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>Order Number</th>
                <th>Customer</th>
                <th>Warehouse</th>
                <th>Order Date</th>
                <th>Total Value</th>
                <th>Fulfillment</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Workflow Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Querying sales orders...' : 'No sales orders found.'}
                  </td>
                </tr>
              ) : (
                orders.map((so) => {
                  const totalOrdered = so.items?.reduce((s, it) => s + it.quantity_ordered, 0) || 0;
                  const totalShipped = so.items?.reduce((s, it) => s + it.quantity_shipped, 0) || 0;

                  return (
                    <tr key={so.id}>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'monospace' }}>
                          {so.order_number}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{so.customer?.name || 'Customer'}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{so.customer?.code}</div>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{so.warehouse?.code}</span>
                      </td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        {so.order_date ? new Date(so.order_date).toLocaleDateString() : '-'}
                      </td>
                      <td>
                        <strong>${Number(so.total_amount).toFixed(2)}</strong>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.8rem', marginBottom: '2px' }}>
                          <span>{totalShipped}</span> / <span>{totalOrdered}</span> units
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
                              width: totalOrdered > 0 ? `${(totalShipped / totalOrdered) * 100}%` : '0%',
                              height: '100%',
                              background: totalShipped === totalOrdered ? 'var(--status-success)' : 'var(--accent-primary)',
                            }}
                          />
                        </div>
                      </td>
                      <td>{getStatusBadge(so.status)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          {so.status === 'DRAFT' && (
                            <button
                              onClick={() => handleConfirmSO(so.id)}
                              className="btn btn-primary"
                              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            >
                              <FileCheck2 size={13} />
                              <span>Reserve & Confirm</span>
                            </button>
                          )}

                          {(so.status === 'CONFIRMED' || so.status === 'PARTIAL') && (
                            <button
                              onClick={() => handleOpenShipment(so)}
                              className="btn btn-primary"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', background: 'var(--accent-secondary)', borderColor: 'var(--accent-secondary)' }}
                            >
                              <Truck size={13} />
                              <span>Dispatch</span>
                            </button>
                          )}

                          {so.status !== 'SHIPPED' && so.status !== 'CANCELLED' && (
                            <button
                              onClick={() => handleCancelSO(so.id)}
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', color: 'var(--status-danger)' }}
                              title="Cancel Order"
                            >
                              <Ban size={13} />
                            </button>
                          )}

                          <button
                            onClick={() => setSelectedOrder(so)}
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            title="View SO Details"
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

      {/* Create SO Modal */}
      {isCreateOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '720px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Create Sales Order</h3>
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
                  <label className="form-label">Customer *</label>
                  <select
                    className="form-control"
                    required
                    value={soForm.customer_id}
                    onChange={(e) => setSoForm({ ...soForm, customer_id: e.target.value })}
                  >
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} - {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Dispatch Warehouse *</label>
                  <select
                    className="form-control"
                    required
                    value={soForm.warehouse_id}
                    onChange={(e) => setSoForm({ ...soForm, warehouse_id: e.target.value })}
                  >
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.code} - {w.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Order Items */}
              <div style={{ marginTop: 'var(--spacing-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>Line Items to Sell *</label>
                  <button type="button" onClick={addItemToSO} className="btn btn-outline" style={{ padding: '4px 8px', fontSize: '0.75rem' }}>
                    <Plus size={13} />
                    <span>Add Item</span>
                  </button>
                </div>

                {soForm.items.map((item, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 'var(--spacing-sm)', alignItems: 'center', marginBottom: '8px' }}>
                    <select
                      className="form-control"
                      required
                      value={item.product_id}
                      onChange={(e) => {
                        const prod = products.find((p) => p.id === e.target.value);
                        const updated = [...soForm.items];
                        updated[idx].product_id = e.target.value;
                        if (prod) updated[idx].unit_price = Number(prod.selling_price);
                        setSoForm({ ...soForm, items: updated });
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
                        const updated = [...soForm.items];
                        updated[idx].quantity_ordered = parseInt(e.target.value) || 1;
                        setSoForm({ ...soForm, items: updated });
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
                        const updated = [...soForm.items];
                        updated[idx].unit_price = parseFloat(e.target.value) || 0;
                        setSoForm({ ...soForm, items: updated });
                      }}
                    />

                    {soForm.items.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeItemFromSO(idx)}
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
                <label className="form-label">Order Notes / Customer Instructions</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={soForm.notes}
                  onChange={(e) => setSoForm({ ...soForm, notes: e.target.value })}
                />
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsCreateOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Submit Sales Order
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Shipment Dispatch Modal */}
      {isShipmentOpen && selectedOrder && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Dispatch Shipment for {selectedOrder.order_number}</h3>
              <button
                onClick={() => setIsShipmentOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleShipmentSubmit}>
              <div style={{ marginBottom: 'var(--spacing-md)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Dispatching from: <strong style={{ color: 'var(--text-main)' }}>{selectedOrder.warehouse?.name}</strong>. Stock will be deducted from both Reserved and On-Hand balances.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Logistics Carrier</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    value={shipmentForm.carrier}
                    onChange={(e) => setShipmentForm({ ...shipmentForm, carrier: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Tracking Number</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    value={shipmentForm.tracking_number}
                    onChange={(e) => setShipmentForm({ ...shipmentForm, tracking_number: e.target.value })}
                  />
                </div>
              </div>

              <div className="table-responsive" style={{ marginBottom: 'var(--spacing-md)' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Pending Ship</th>
                      <th>Units Dispatched Now</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shipmentForm.items.map((item, idx) => (
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
                            value={item.quantity_to_ship}
                            onChange={(e) => {
                              const updated = [...shipmentForm.items];
                              updated[idx].quantity_to_ship = parseInt(e.target.value) || 0;
                              setShipmentForm({ ...shipmentForm, items: updated });
                            }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsShipmentOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ background: 'var(--accent-secondary)', borderColor: 'var(--accent-secondary)' }}>
                  Confirm & Dispatch Shipment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SO Detail View Modal */}
      {selectedOrder && !isShipmentOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div className="modal-header">
              <div>
                <h3 className="modal-title">{selectedOrder.order_number}</h3>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Customer: {selectedOrder.customer?.name} &bull; Warehouse: {selectedOrder.warehouse?.name}
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
                    <th>Reserved</th>
                    <th>Shipped</th>
                    <th>Unit Price</th>
                    <th>Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedOrder.items.map((it) => (
                    <tr key={it.id}>
                      <td>{it.product?.name || it.product_id}</td>
                      <td>{it.quantity_ordered}</td>
                      <td>{it.quantity_reserved}</td>
                      <td>{it.quantity_shipped}</td>
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
