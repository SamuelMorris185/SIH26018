import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  Filter,
  RefreshCw,
  ExternalLink,
  Layers,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { discrepanciesApi, DiscrepancyFilterParams } from '../api/discrepancies';
import { useNavigation } from '../context/NavigationContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Discrepancy } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';

export const DiscrepanciesList: React.FC = () => {
  const { navigate } = useNavigation();
  const { hasRole } = useAuth();
  const { success, error: toastError } = useToast();

  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState<string>('OPEN');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  // Status transition modal
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<Discrepancy | null>(null);
  const [targetStatus, setTargetStatus] = useState<string>('RESOLVED');
  const [resolutionNotes, setResolutionNotes] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const canReview = hasRole('ADMIN', 'REVIEWER');

  const fetchDiscrepancies = useCallback(async () => {
    setLoading(true);
    try {
      const params: DiscrepancyFilterParams = {
        limit: 100,
      };
      if (statusFilter) params.status = statusFilter;
      if (severityFilter) params.severity = severityFilter;
      if (typeFilter) params.discrepancy_type = typeFilter;

      const response = await discrepanciesApi.listDiscrepancies(params);
      setDiscrepancies(response.data || []);
      setTotal(response.total || 0);
    } catch (err: any) {
      toastError(err?.message || 'Failed to load discrepancies');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter, typeFilter, toastError]);

  useEffect(() => {
    fetchDiscrepancies();
  }, [fetchDiscrepancies]);

  const handleStatusUpdate = async () => {
    if (!selectedDiscrepancy) return;
    setActionLoading(true);
    try {
      await discrepanciesApi.updateDiscrepancyStatus(
        selectedDiscrepancy.id,
        targetStatus,
        resolutionNotes
      );
      success(`Discrepancy transitioned to ${targetStatus}`);
      setSelectedDiscrepancy(null);
      setResolutionNotes('');
      fetchDiscrepancies();
    } catch (err: any) {
      toastError(err?.message || 'Status transition rejected');
    } finally {
      setActionLoading(false);
    }
  };

  const criticalCount = discrepancies.filter((d) => d.severity === 'CRITICAL').length;
  const highCount = discrepancies.filter((d) => d.severity === 'HIGH').length;
  const mediumCount = discrepancies.filter((d) => d.severity === 'MEDIUM').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Title & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Discrepancy Intelligence Hub
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
            Cross-document ownership conflicts, area discrepancies, and statutory anomalies
          </p>
        </div>

        <button
          onClick={fetchDiscrepancies}
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
          <span>Refresh</span>
        </button>
      </div>

      {/* Severity Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div
          className="glass-panel"
          style={{
            padding: '1.25rem',
            backgroundColor: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fecdd3' }}>Critical Severity</span>
            <AlertTriangle size={18} color="#f43f5e" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fb7185', marginTop: '0.5rem' }}>
            {criticalCount}
          </div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: '1.25rem',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            border: '1px solid rgba(249, 115, 22, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fed7aa' }}>High Severity</span>
            <AlertTriangle size={18} color="#f97316" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fdba74', marginTop: '0.5rem' }}>
            {highCount}
          </div>
        </div>

        <div
          className="glass-panel"
          style={{
            padding: '1.25rem',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fef08a' }}>Medium Severity</span>
            <AlertTriangle size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fbbf24', marginTop: '0.5rem' }}>
            {mediumCount}
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Filter size={16} color="#64748b" />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1' }}>Filters:</span>
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
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
          <option value="">All Statuses</option>
          <option value="OPEN">OPEN Only</option>
          <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="DISMISSED">DISMISSED</option>
        </select>

        {/* Severity Filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
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
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>

        {/* Type Filter */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
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
          <option value="">All Types</option>
          <option value="OWNER_MISMATCH">Owner Mismatch</option>
          <option value="CO_OWNER_MISMATCH">Co-Owner Mismatch</option>
          <option value="AREA_MISMATCH">Area Mismatch</option>
          <option value="SURVEY_CONFLICT">Survey Conflict</option>
          <option value="DUPLICATE_DOCUMENT">Duplicate Document</option>
          <option value="LOW_CONFIDENCE_CRITICAL_FIELD">Low Confidence Critical</option>
        </select>
      </div>

      {/* Discrepancy Cards List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {loading ? (
          [...Array(4)].map((_, i) => (
            <div key={i} className="glass-panel" style={{ height: '130px', opacity: 0.5 }} />
          ))
        ) : discrepancies.length === 0 ? (
          <div className="glass-panel" style={{ padding: '3.5rem', textAlign: 'center', color: '#64748b' }}>
            <CheckCircle2 size={36} color="#10b981" style={{ margin: '0 auto 0.75rem auto' }} />
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
              No Discrepancies Match the Current Filter
            </div>
            <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
              Select a different filter combination or inspect new records.
            </p>
          </div>
        ) : (
          discrepancies.map((disc) => (
            <div
              key={disc.id}
              className="glass-panel"
              style={{
                padding: '1.25rem 1.5rem',
                borderLeft: `4px solid ${
                  disc.severity === 'CRITICAL'
                    ? '#f43f5e'
                    : disc.severity === 'HIGH'
                    ? '#f97316'
                    : '#fbbf24'
                }`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.98rem', color: '#f8fafc' }}>
                    {disc.discrepancy_type}
                  </span>
                  <StatusBadge status={disc.severity} size="sm" />
                  <StatusBadge status={disc.status} size="sm" />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <button
                    onClick={() => navigate('record-detail', { recordId: disc.record_id })}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      backgroundColor: 'rgba(56, 189, 248, 0.1)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      color: '#38bdf8',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <span>View Record</span>
                    <ExternalLink size={12} />
                  </button>

                  {canReview && (
                    <button
                      onClick={() => {
                        setSelectedDiscrepancy(disc);
                        setTargetStatus(disc.status === 'OPEN' ? 'RESOLVED' : 'ACKNOWLEDGED');
                      }}
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        color: '#f8fafc',
                        padding: '0.4rem 0.85rem',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Update Lifecycle Status
                    </button>
                  )}
                </div>
              </div>

              <p style={{ fontSize: '0.88rem', color: '#cbd5e1', marginTop: '0.65rem' }}>
                {disc.description}
              </p>

              {(disc.source_value || disc.conflicting_value) && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '1rem',
                    marginTop: '0.85rem',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    borderRadius: '8px',
                    fontSize: '0.82rem',
                  }}
                >
                  <div>
                    <span style={{ color: '#94a3b8', fontSize: '0.72rem', display: 'block' }}>
                      Current Document Claim:
                    </span>
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>{disc.source_value || '—'}</span>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8', fontSize: '0.72rem', display: 'block' }}>
                      Existing Title Record:
                    </span>
                    <span style={{ color: '#fb7185', fontWeight: 600 }}>{disc.conflicting_value || '—'}</span>
                  </div>
                </div>
              )}

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1.5rem',
                  marginTop: '0.85rem',
                  fontSize: '0.75rem',
                  color: '#64748b',
                }}
              >
                <span>Record ID: {disc.record_id}</span>
                <span>Detected: {new Date(disc.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal: Update Discrepancy Status */}
      {selectedDiscrepancy && (
        <Modal
          isOpen={!!selectedDiscrepancy}
          onClose={() => setSelectedDiscrepancy(null)}
          title={`Update Status: ${selectedDiscrepancy.discrepancy_type}`}
        >
          <div>
            <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '1rem' }}>
              {selectedDiscrepancy.description}
            </div>

            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
              Target Resolution Status
            </label>
            <select
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value)}
              style={{
                width: '100%',
                padding: '0.65rem 0.75rem',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
                marginBottom: '1rem',
              }}
            >
              <option value="ACKNOWLEDGED">ACKNOWLEDGED (Under investigation)</option>
              <option value="RESOLVED">RESOLVED (Reconciled with revenue records)</option>
              <option value="DISMISSED">DISMISSED (False positive / legal exception)</option>
              <option value="OPEN">OPEN (Re-open for review)</option>
            </select>

            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
              Resolution Notes (Optional)
            </label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="e.g. Discrepancy reconciled via Registered Sale Deed #4501..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
              <button
                onClick={() => setSelectedDiscrepancy(null)}
                style={{
                  padding: '0.6rem 1.1rem',
                  backgroundColor: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: '8px',
                  color: '#e2e8f0',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleStatusUpdate}
                disabled={actionLoading}
                style={{
                  padding: '0.6rem 1.4rem',
                  backgroundColor: '#0284c7',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                  fontWeight: 700,
                  cursor: actionLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {actionLoading ? 'Updating...' : 'Confirm Update'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
