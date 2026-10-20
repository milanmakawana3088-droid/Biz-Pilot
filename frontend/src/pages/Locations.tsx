import React, { useEffect, useState } from 'react';
import { Building2, CheckCircle2, MapPin, Plus, RefreshCw, Warehouse as WhIcon, X } from 'lucide-react';
import { api } from '@/lib/api';
import { Location, Warehouse } from '@/types';

export const Locations: React.FC = () => {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'WAREHOUSE' | 'LOCATION'>('WAREHOUSE');

  const [whForm, setWhForm] = useState({
    code: '',
    name: '',
    location_id: '',
  });

  const [locForm, setLocForm] = useState({
    code: '',
    name: '',
    city: '',
    country: 'USA',
  });

  const [message, setMessage] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [whList, locList] = await Promise.all([
        api.warehouses.list(),
        api.locations.list(),
      ]);
      setWarehouses(whList || []);
      setLocations(locList || []);
      if (locList && locList.length > 0 && !whForm.location_id) {
        setWhForm((prev) => ({ ...prev, location_id: locList[0].id }));
      }
    } catch (err) {
      console.error('Failed to load locations', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenWarehouseModal = () => {
    setModalType('WAREHOUSE');
    setWhForm({
      code: '',
      name: '',
      location_id: locations[0]?.id || '',
    });
    setIsModalOpen(true);
  };

  const handleOpenLocationModal = () => {
    setModalType('LOCATION');
    setLocForm({
      code: '',
      name: '',
      city: '',
      country: 'USA',
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      if (modalType === 'WAREHOUSE') {
        await api.warehouses.create({
          code: whForm.code.toUpperCase(),
          name: whForm.name,
          location_id: whForm.location_id,
        });
        setMessage(`Warehouse ${whForm.code} created successfully.`);
      } else {
        await api.locations.create({
          code: locForm.code.toUpperCase(),
          name: locForm.name,
          city: locForm.city,
          country: locForm.country,
        });
        setMessage(`Location facility ${locForm.code} created successfully.`);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setMessage(`Error: ${err.message || 'Operation failed'}`);
    }
  };

  return (
    <div>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', flexWrap: 'wrap', gap: 'var(--spacing-md)' }}>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', margin: 0 }}>
          Manage global enterprise facilities, regional distribution centers, and warehouse storage locations.
        </p>

        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button onClick={loadData} className="btn btn-outline" title="Refresh">
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Sync</span>
          </button>
          <button onClick={handleOpenLocationModal} className="btn btn-outline">
            <MapPin size={15} />
            <span>Add Facility Location</span>
          </button>
          <button onClick={handleOpenWarehouseModal} className="btn btn-primary">
            <Plus size={15} />
            <span>Add Warehouse</span>
          </button>
        </div>
      </div>

      {message && (
        <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--status-success)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: 'var(--spacing-md)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
          {message}
        </div>
      )}

      {/* Warehouses Grid */}
      <div style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: 'var(--spacing-md)' }}>
          Active Warehouses ({warehouses.length})
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--spacing-md)' }}>
          {warehouses.map((wh) => (
            <div key={wh.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-primary">{wh.code}</span>
                <span className={`badge ${wh.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {wh.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)', margin: '4px 0' }}>
                {wh.name}
              </h4>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={13} color="var(--accent-secondary)" />
                <span>Facility Location ID: {wh.location_id}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid var(--border-color)' }}>
                Registered on {new Date(wh.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Locations Facility Table */}
      <div>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: 'var(--spacing-md)' }}>
          Physical Facilities & Locations ({locations.length})
        </h3>
        <div className="card" style={{ padding: 0 }}>
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Facility Name</th>
                  <th>City</th>
                  <th>Country</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {locations.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: 'var(--spacing-lg)', color: 'var(--text-muted)' }}>
                      No facility locations registered.
                    </td>
                  </tr>
                ) : (
                  locations.map((loc) => (
                    <tr key={loc.id}>
                      <td>
                        <strong style={{ color: 'var(--accent-secondary)' }}>{loc.code}</strong>
                      </td>
                      <td>{loc.name}</td>
                      <td>{loc.city || '-'}</td>
                      <td>{loc.country}</td>
                      <td>
                        <span className={`badge ${loc.is_active ? 'badge-success' : 'badge-danger'}`}>
                          {loc.is_active ? 'Operating' : 'Closed'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Creation Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 className="modal-title">
                {modalType === 'WAREHOUSE' ? 'Register New Warehouse' : 'Create Facility Location'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn btn-outline"
                style={{ padding: '4px', border: 'none', background: 'transparent', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {modalType === 'WAREHOUSE' ? (
                <>
                  <div className="form-group">
                    <label className="form-label">Warehouse Code *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. WH-EAST"
                      value={whForm.code}
                      onChange={(e) => setWhForm({ ...whForm, code: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Warehouse Name *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. East Coast Distribution Center"
                      value={whForm.name}
                      onChange={(e) => setWhForm({ ...whForm, name: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Assigned Facility Location *</label>
                    <select
                      className="form-control"
                      required
                      value={whForm.location_id}
                      onChange={(e) => setWhForm({ ...whForm, location_id: e.target.value })}
                    >
                      {locations.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.code} - {l.name} ({l.city || l.country})
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              ) : (
                <>
                  <div className="form-group">
                    <label className="form-label">Location Code *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. LOC-NYC"
                      value={locForm.code}
                      onChange={(e) => setLocForm({ ...locForm, code: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Facility Name *</label>
                    <input
                      type="text"
                      required
                      className="form-control"
                      placeholder="e.g. New York Logistics Hub"
                      value={locForm.name}
                      onChange={(e) => setLocForm({ ...locForm, name: e.target.value })}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                    <div className="form-group">
                      <label className="form-label">City</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Brooklyn"
                        value={locForm.city}
                        onChange={(e) => setLocForm({ ...locForm, city: e.target.value })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Country</label>
                      <input
                        type="text"
                        className="form-control"
                        value={locForm.country}
                        onChange={(e) => setLocForm({ ...locForm, country: e.target.value })}
                      />
                    </div>
                  </div>
                </>
              )}

              <div className="modal-footer" style={{ marginTop: 'var(--spacing-lg)' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Facility
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
