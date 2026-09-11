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
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <Lock size={36} color="#f43f5e" style={{ margin: '0 auto 0.75rem auto' }} />
        <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>Access Prohibited</h3>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '4px' }}>
          Compliance audit logs are restricted strictly to System Administrators.
        </p>
      </div>
    );
  }

  const totalPages = Math.ceil(total / limit) || 1;

  const actionColors: Record<string, { bg: string; text: string }> = {
    LOGIN_SUCCESS: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399' },
    LOGIN_FAILURE: { bg: 'rgba(244, 63, 94, 0.15)', text: '#fb7185' },
    RECORD_APPROVED: { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399' },
    RECORD_REJECTED: { bg: 'rgba(244, 63, 94, 0.2)', text: '#fb7185' },
    RECORD_VALIDATED: { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8' },
    RECORD_FLAGGED: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24' },
    DISCREPANCY_STATUS_UPDATED: { bg: 'rgba(168, 85, 247, 0.15)', text: '#c084fc' },
    DOCUMENT_CREATED: { bg: 'rgba(56, 189, 248, 0.12)', text: '#38bdf8' },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              padding: '0.6rem',
              borderRadius: '10px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Shield size={22} color="#f87171" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Immutable Compliance Audit Trail
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
              Cryptographically timestamped, append-only logs for legal governance and security verification
            </p>
          </div>
        </div>

        <button
          onClick={fetchLogs}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            color: '#e2e8f0',
            padding: '0.5rem 0.9rem',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Filter size={16} color="#64748b" />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1' }}>Filters:</span>
        </div>

        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          style={{
            padding: '0.55rem 0.85rem',
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '8px',
            color: '#e2e8f0',
            fontSize: '0.85rem',
            outline: 'none',
          }}
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
          style={{
            padding: '0.55rem 0.85rem',
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '8px',
            color: '#e2e8f0',
            fontSize: '0.85rem',
            outline: 'none',
          }}
        >
          <option value="">All Entity Types</option>
          <option value="LAND_RECORD">LAND_RECORD</option>
          <option value="DISCREPANCY">DISCREPANCY</option>
          <option value="DOCUMENT">DOCUMENT</option>
          <option value="USER">USER</option>
        </select>
      </div>

      {/* Logs Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.72rem',
                color: '#94a3b8',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              <th style={{ padding: '0.9rem 1.25rem' }}>Timestamp</th>
              <th style={{ padding: '0.9rem 1rem' }}>Action Event</th>
              <th style={{ padding: '0.9rem 1rem' }}>Resource Type</th>
              <th style={{ padding: '0.9rem 1rem' }}>Entity UUID</th>
              <th style={{ padding: '0.9rem 1rem' }}>Actor UUID</th>
              <th style={{ padding: '0.9rem 1.25rem' }}>State Transition Summary</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td colSpan={6} style={{ padding: '1.25rem' }}>
                    <div style={{ height: '18px', backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: '4px' }} />
                  </td>
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                  <History size={36} color="#334155" style={{ margin: '0 auto 0.75rem auto' }} />
                  <div style={{ fontWeight: 600, color: '#94a3b8' }}>No Audit Logs Found</div>
                </td>
              </tr>
            ) : (
              logs.map((log) => {
                const badge = actionColors[log.action] || {
                  bg: 'rgba(255, 255, 255, 0.08)',
                  text: '#e2e8f0',
                };
                const summary =
                  log.new_state
                    ? JSON.stringify(log.new_state)
                    : log.metadata_json
                    ? JSON.stringify(log.metadata_json)
                    : '—';

                return (
                  <tr
                    key={log.id}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      fontSize: '0.82rem',
                    }}
                  >
                    <td style={{ padding: '0.9rem 1.25rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.9rem 1rem' }}>
                      <span
                        style={{
                          backgroundColor: badge.bg,
                          color: badge.text,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          letterSpacing: '0.03em',
                        }}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td style={{ padding: '0.9rem 1rem', color: '#cbd5e1', fontWeight: 600 }}>
                      {log.entity_type}
                    </td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'monospace', color: '#64748b', fontSize: '0.75rem' }}>
                      {log.entity_id ? String(log.entity_id).substring(0, 8) + '...' : '—'}
                    </td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'monospace', color: '#64748b', fontSize: '0.75rem' }}>
                      {log.actor_user_id ? String(log.actor_user_id).substring(0, 8) + '...' : 'SYSTEM'}
                    </td>
                    <td
                      style={{
                        padding: '0.9rem 1.25rem',
                        color: '#94a3b8',
                        maxWidth: '260px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontFamily: 'monospace',
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
              backgroundColor: 'rgba(15, 23, 42, 0.5)',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Showing {Math.min((page - 1) * limit + 1, total)} to {Math.min(page * limit, total)} of{' '}
              {total} audit entries
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.4rem 0.6rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  color: page <= 1 ? '#475569' : '#e2e8f0',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer',
                }}
              >
                <ChevronLeft size={16} />
              </button>

              <span style={{ fontSize: '0.8rem', color: '#cbd5e1', padding: '0 4px' }}>
                Page {page} of {totalPages}
              </span>

              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.4rem 0.6rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  color: page >= totalPages ? '#475569' : '#e2e8f0',
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                }}
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
