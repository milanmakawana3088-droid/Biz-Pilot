import React, { useEffect, useState } from 'react';
import { Edit2, Filter, Package, Plus, Search, Tag, X } from 'lucide-react';
import { api } from '@/lib/api';
import { Product, ProductCategory } from '@/types';

export const Products: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [uoms, setUoms] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState({
    sku: '',
    barcode: '',
    name: '',
    description: '',
    category_id: '',
    unit_of_measure: 'PCS',
    cost_price: 0,
    selling_price: 0,
    reorder_point: 10,
    safety_stock: 5,
  });

  const loadProducts = async () => {
    setIsLoading(true);
    try {
      const res = await api.products.list({
        search: search || undefined,
        category_id: selectedCategory || undefined,
        size: 100,
      });
      setProducts(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load products');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMetadata = async () => {
    try {
      const [cats, uomList] = await Promise.all([
        api.products.categories().catch(() => []),
        api.products.uoms().catch(() => []),
      ]);
      setCategories(cats || []);
      setUoms(uomList || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadMetadata();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [search, selectedCategory]);

  const handleOpenCreate = () => {
    setFormData({
      sku: '',
      barcode: '',
      name: '',
      description: '',
      category_id: categories[0]?.id ? String(categories[0].id) : '',
      unit_of_measure: uoms[0]?.code || 'PCS',
      cost_price: 0,
      selling_price: 0,
      reorder_point: 10,
      safety_stock: 5,
    });
    setEditingProduct(null);
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (p: Product) => {
    setEditingProduct(p);
    setFormData({
      sku: p.sku,
      barcode: p.barcode || '',
      name: p.name,
      description: p.description || '',
      category_id: p.category_id ? String(p.category_id) : '',
      unit_of_measure: p.unit_of_measure,
      cost_price: Number(p.cost_price),
      selling_price: Number(p.selling_price),
      reorder_point: p.reorder_point,
      safety_stock: p.safety_stock,
    });
    setIsCreateOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (editingProduct) {
        await api.products.update(editingProduct.id, {
          name: formData.name,
          description: formData.description,
          cost_price: Number(formData.cost_price),
          selling_price: Number(formData.selling_price),
          reorder_point: Number(formData.reorder_point),
          safety_stock: Number(formData.safety_stock),
        });
      } else {
        await api.products.create({
          sku: formData.sku.toUpperCase(),
          barcode: formData.barcode || undefined,
          name: formData.name,
          description: formData.description,
          category_id: formData.category_id || undefined,
          unit_of_measure: formData.unit_of_measure,
          cost_price: Number(formData.cost_price),
          selling_price: Number(formData.selling_price),
          reorder_point: Number(formData.reorder_point),
          safety_stock: Number(formData.safety_stock),
        });
      }
      setIsCreateOpen(false);
      loadProducts();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    }
  };

  return (
    <div>
      {/* Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flex: 1, maxWidth: '600px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by SKU, Barcode, or Product Name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <select
            className="form-control"
            style={{ width: '180px' }}
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <button onClick={handleOpenCreate} className="btn btn-primary">
          <Plus size={16} />
          <span>New Product SKU</span>
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--status-danger)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: 'var(--spacing-md)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          {error}
        </div>
      )}

      {/* Products Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>UOM</th>
                <th>Cost Price</th>
                <th>Selling Price</th>
                <th>Reorder Pt</th>
                <th>Safety Stock</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Loading product catalog...' : 'No products found matching criteria.'}
                  </td>
                </tr>
              ) : (
                products.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--accent-secondary)' }}>{p.sku}</div>
                      {p.barcode && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{p.barcode}</div>}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{p.name}</div>
                      {p.description && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.description}</div>}
                    </td>
                    <td>
                      <span className="badge badge-neutral">
                        {p.category?.name || 'Uncategorized'}
                      </span>
                    </td>
                    <td>{p.unit_of_measure}</td>
                    <td>${Number(p.cost_price).toFixed(2)}</td>
                    <td>${Number(p.selling_price).toFixed(2)}</td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{p.reorder_point}</span>
                    </td>
                    <td>{p.safety_stock}</td>
                    <td>
                      <span className={`badge ${p.is_active ? 'badge-success' : 'badge-danger'}`}>
                        {p.is_active ? 'Active' : 'Archived'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => handleOpenEdit(p)}
                        className="btn btn-outline"
                        style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                      >
                        <Edit2 size={13} />
                        <span>Edit</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Modal */}
      {isCreateOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingProduct ? `Edit Product: ${editingProduct.sku}` : 'Register New Product'}
              </h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">SKU Code *</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingProduct}
                    className="form-control"
                    placeholder="e.g. LAPTOP-PRO-16"
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Barcode / UPC</label>
                  <input
                    type="text"
                    disabled={!!editingProduct}
                    className="form-control"
                    placeholder="e.g. 793573195021"
                    value={formData.barcode}
                    onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Product Name *</label>
                <input
                  type="text"
                  required
                  className="form-control"
                  placeholder="e.g. Precision Workstation 16-inch 32GB"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  rows={2}
                  placeholder="Technical specifications, features, or storage guidelines..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select
                    className="form-control"
                    disabled={!!editingProduct}
                    value={formData.category_id}
                    onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                  >
                    <option value="">Select Category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Unit of Measure (UOM)</label>
                  <select
                    className="form-control"
                    disabled={!!editingProduct}
                    value={formData.unit_of_measure}
                    onChange={(e) => setFormData({ ...formData, unit_of_measure: e.target.value })}
                  >
                    <option value="PCS">Pieces (PCS)</option>
                    <option value="BOX">Box (BOX)</option>
                    <option value="KG">Kilogram (KG)</option>
                    <option value="MTR">Meter (MTR)</option>
                    <option value="SET">Set (SET)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Cost Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    className="form-control"
                    value={formData.cost_price}
                    onChange={(e) => setFormData({ ...formData, cost_price: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Selling Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    className="form-control"
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                <div className="form-group">
                  <label className="form-label">Reorder Point Threshold</label>
                  <input
                    type="number"
                    min="0"
                    required
                    className="form-control"
                    value={formData.reorder_point}
                    onChange={(e) => setFormData({ ...formData, reorder_point: parseInt(e.target.value) || 0 })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Safety Stock</label>
                  <input
                    type="number"
                    min="0"
                    required
                    className="form-control"
                    value={formData.safety_stock}
                    onChange={(e) => setFormData({ ...formData, safety_stock: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsCreateOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingProduct ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
