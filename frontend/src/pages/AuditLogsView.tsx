import React, { useState, useEffect, useCallback } from 'react';
import { History, Shield, RefreshCw, Filter, ChevronLeft, ChevronRight, Lock } from 'lucide-react';
import { auditApi, AuditLogFilterParams } from '../api/audit';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { AuditLog } from '../types';

export const AuditLogsView: React.FC = () => {
  const { isAdmin } = useAuth();
  const { error: toastError } = useToast();

  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(25);
  const [actionFilter, setActionFilter] = useState<string>('');
  const [entityFilter, setEntityFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: AuditLogFilterParams = {
        page,
        limit,
      };
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;

      const res = await auditApi.getAuditLogs(params);
      setLogs(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      toastError(err?.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [page, limit, actionFilter, entityFilter, toastError]);

  useEffect(() => {
    if (isAdmin) {
      fetchLogs();
    }
  }, [isAdmin, fetchLogs]);

  if (!isAdmin) {
    return (
      <div className="bento-card" style={{ padding: '3.5rem', textAlign: 'center' }}>
        <Lock size={40} color="#f43f5e" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ fontSize: '1.25rem', color: '#f8fafc', fontWeight: 700 }}>Access Prohibited</h3>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '6px' }}>
          Compliance audit logs are restricted strictly to System Administrators.
        </p>
      </div>
    );
  }

  const totalPages = Math.ceil(total / limit) || 1;

  const actionColors: Record<string, { bg: string; text: string; border: string }> = {
    LOGIN_SUCCESS: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' },
    LOGIN_FAILURE: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.3)' },
    RECORD_APPROVED: { bg: 'rgba(16, 185, 129, 0.18)', text: '#34d399', border: 'rgba(16, 185, 129, 0.35)' },
    RECORD_REJECTED: { bg: 'rgba(239, 68, 68, 0.18)', text: '#f87171', border: 'rgba(239, 68, 68, 0.35)' },
    RECORD_VALIDATED: { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' },
    RECORD_FLAGGED: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' },
    DISCREPANCY_STATUS_UPDATED: { bg: 'rgba(99, 102, 241, 0.15)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.3)' },
    DOCUMENT_CREATED: { bg: 'rgba(56, 189, 248, 0.12)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.25)' },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '12px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Shield size={24} color="#f87171" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Immutable Compliance Audit Trail
            </h2>
            <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '3px' }}>
              Timestamped audit events for record changes, review decisions, and authentication
            </p>
          </div>
        </div>

        <button
          onClick={fetchLogs}
          className="btn btn-secondary"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div
        className="bento-card"
        style={{
          padding: '1.1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Filter size={16} color="#64748b" />
          <span className="font-mono" style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            // LEDGER FILTERS:
          </span>
        </div>

        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          style={{ maxWidth: '220px' }}
        >
          <option value="">All Actions</option>
          <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
          <option value="RECORD_APPROVED">RECORD_APPROVED</option>
          <option value="RECORD_REJECTED">RECORD_REJECTED</option>
          <option value="RECORD_VALIDATED">RECORD_VALIDATED</option>
          <option value="RECORD_FLAGGED">RECORD_FLAGGED</option>
          <option value="DISCREPANCY_STATUS_UPDATED">DISCREPANCY_STATUS_UPDATED</option>
          <option value="DOCUMENT_CREATED">DOCUMENT_CREATED</option>
        </select>

        <select
          value={entityFilter}
          onChange={(e) => {
            setEntityFilter(e.target.value);
            setPage(1);
          }}
          style={{ maxWidth: '220px' }}
        >
          <option value="">All Entity Types</option>
          <option value="LAND_RECORD">LAND_RECORD</option>
          <option value="DISCREPANCY">DISCREPANCY</option>
          <option value="DOCUMENT">DOCUMENT</option>
          <option value="USER">USER</option>
        </select>
      </div>

      {/* Logs Table */}
      <div className="bento-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              <th>TIMESTAMP</th>
              <th>ACTION EVENT</th>
              <th>RESOURCE TYPE</th>
              <th>ENTITY UUID</th>
              <th>ACTOR UUID</th>
              <th>STATE TRANSITION SUMMARY</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i}>
                  <td colSpan={6} style={{ padding: '1.25rem' }}>
                    <div style={{ height: '18px', borderRadius: '4px' }} className="skeleton-shimmer" />
                  </td>
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '3.5rem', textAlign: 'center', color: '#64748b' }}>
                  <History size={40} color="#334155" style={{ margin: '0 auto 0.75rem auto' }} />
                  <div style={{ fontWeight: 600, color: '#94a3b8' }}>No Audit Logs Found</div>
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const badge = actionColors[log.action] || {
                  bg: 'rgba(255, 255, 255, 0.08)',
                  text: '#f8fafc',
                  border: 'rgba(255, 255, 255, 0.12)',
                };
                const summary =
                  log.new_state
                    ? JSON.stringify(log.new_state)
                    : log.metadata_json
                    ? JSON.stringify(log.metadata_json)
                    : '—';

                return (
                  <tr key={log.id}>
                    <td className="font-mono" style={{ padding: '0.9rem 1.25rem', color: '#94a3b8', whiteSpace: 'nowrap', fontSize: '0.78rem' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.9rem 1rem' }}>
                      <span
                        className="font-mono"
                        style={{
                          backgroundColor: badge.bg,
                          color: badge.text,
                          border: `1px solid ${badge.border}`,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          fontSize: '0.72rem',
                          letterSpacing: '0.04em',
                        }}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="font-mono" style={{ padding: '0.9rem 1rem', color: '#cbd5e1', fontWeight: 600, fontSize: '0.8rem' }}>
                      {log.entity_type}
                    </td>
                    <td className="font-mono" style={{ padding: '0.9rem 1rem', color: '#64748b', fontSize: '0.75rem' }}>
                      {log.entity_id ? String(log.entity_id).substring(0, 8) + '...' : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '0.9rem 1rem', color: '#64748b', fontSize: '0.75rem' }}>
                      {log.actor_user_id ? String(log.actor_user_id).substring(0, 8) + '...' : 'SYSTEM'}
                    </td>
                    <td
                      className="font-mono"
                      style={{
                        padding: '0.9rem 1.25rem',
                        color: '#94a3b8',
                        maxWidth: '260px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontSize: '0.75rem',
                      }}
                      title={summary}
                    >
                      {summary}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Pagination Bar */}
        {total > limit && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.85rem 1.25rem',
              backgroundColor: 'rgba(15, 23, 42, 0.6)',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <div className="font-mono" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              Showing {Math.min((page - 1) * limit + 1, total)} to {Math.min(page * limit, total)} of{' '}
              {total} audit entries
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="btn btn-secondary"
                style={{ padding: '0.35rem 0.6rem' }}
              >
                <ChevronLeft size={16} />
              </button>

              <span className="font-mono" style={{ fontSize: '0.8rem', color: '#cbd5e1', padding: '0 4px' }}>
                Page {page} of {totalPages}
              </span>

              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="btn btn-secondary"
                style={{ padding: '0.35rem 0.6rem' }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
