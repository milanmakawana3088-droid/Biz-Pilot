import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Eye, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { AuditLog } from '@/types';

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [entityFilter, setEntityFilter] = useState('');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const res = await api.audit.list({
        entity_type: entityFilter || undefined,
        size: 100,
      });
      setLogs(res.items || []);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [entityFilter]);

  const toggleExpand = (id: string) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  const getActionBadge = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'CREATE':
        return <span className="badge badge-success">Create</span>;
      case 'UPDATE':
        return <span className="badge badge-info">Update</span>;
      case 'DELETE':
        return <span className="badge badge-danger">Delete</span>;
      case 'ADJUSTMENT':
        return <span className="badge badge-warning">Stock Adjustment</span>;
      case 'TRANSFER':
        return <span className="badge badge-primary">Stock Transfer</span>;
      default:
        return <span className="badge badge-neutral">{action}</span>;
    }
  };

  const filteredLogs = logs.filter((l) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      l.entity_type.toLowerCase().includes(term) ||
      l.entity_id?.toLowerCase().includes(term) ||
      l.actor_email?.toLowerCase().includes(term)
    );
  });

  return (
    <div>
      {/* Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flex: 1, maxWidth: '600px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              className="form-control"
              style={{ paddingLeft: '36px' }}
              placeholder="Search by entity ID, actor email, or entity..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <select
            className="form-control"
            style={{ width: '180px' }}
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
          >
            <option value="">All Entities</option>
            <option value="Product">Products</option>
            <option value="StockLevel">Stock Levels</option>
            <option value="PurchaseOrder">Purchase Orders</option>
            <option value="SalesOrder">Sales Orders</option>
            <option value="Warehouse">Warehouses</option>
          </select>
        </div>

        <button onClick={loadLogs} className="btn btn-outline" title="Refresh">
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          <span>Sync Logs</span>
        </button>
      </div>

      {/* Audit Logs Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}></th>
                <th>Timestamp</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Action</th>
                <th>Actor Email</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: 'var(--spacing-xl)', color: 'var(--text-muted)' }}>
                    {isLoading ? 'Querying system audit log...' : 'No audit records found.'}
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => toggleExpand(log.id)}
                        style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-card-hover)' : undefined }}
                      >
                        <td style={{ textAlign: 'center' }}>
                          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td>
                          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{log.entity_type}</span>
                        </td>
                        <td>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{log.entity_id}</span>
                        </td>
                        <td>{getActionBadge(log.action)}</td>
                        <td>
                          <span style={{ fontSize: '0.85rem' }}>{log.actor_email || 'System'}</span>
                        </td>
                        <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {log.ip_address || '127.0.0.1'}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={{ background: 'var(--bg-base)', padding: 'var(--spacing-md)' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                              RECORD MUTATION PAYLOAD:
                            </div>
                            <pre
                              style={{
                                background: 'rgba(0, 0, 0, 0.4)',
                                padding: '12px',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '0.75rem',
                                color: 'var(--accent-secondary)',
                                overflowX: 'auto',
                                margin: 0,
                              }}
                            >
                              {JSON.stringify(log.changes || {}, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
