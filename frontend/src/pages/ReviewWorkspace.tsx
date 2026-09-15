import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckSquare,
  AlertTriangle,
  FileText,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  ExternalLink,
  Clock,
  Eye,
  ArrowRight,
} from 'lucide-react';
import { recordsApi } from '../api/records';
import { discrepanciesApi } from '../api/discrepancies';
import { reviewApi } from '../api/review';
import { useNavigation } from '../context/NavigationContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { LandRecord, Discrepancy } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';
import { Modal } from '../components/ui/Modal';

export const ReviewWorkspace: React.FC = () => {
  const { navigate } = useNavigation();
  const { hasRole } = useAuth();
  const { success, error: toastError } = useToast();

  const [queue, setQueue] = useState<LandRecord[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<LandRecord | null>(null);
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Modals
  const [isApproveOpen, setIsApproveOpen] = useState<boolean>(false);
  const [isRejectOpen, setIsRejectOpen] = useState<boolean>(false);
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const canReview = hasRole('ADMIN', 'REVIEWER');

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const pendingRecords: LandRecord[] = [];
      let page = 1;
      let totalPages = 1;
      do {
        const res = await recordsApi.listRecords({
          page, limit: 100, review_status: ['PENDING_REVIEW', 'IN_REVIEW'],
        });
        pendingRecords.push(...res.data);
        totalPages = res.total_pages || 1;
        page += 1;
      } while (page <= totalPages);
      setQueue(pendingRecords);
      setSelectedRecord((previous) => pendingRecords.find((r) => r.id === previous?.id) || pendingRecords[0] || null);
    } catch (err: any) {
      toastError(err?.message || 'Failed to load review queue');
    } finally {
      setLoading(false);
    }
  }, [toastError]);

  const selectRecord = (record: LandRecord) => setSelectedRecord(record);

  useEffect(() => {
    let cancelled = false;
    setDiscrepancies([]);
    if (!selectedRecord) return;
    setDetailLoading(true);
    discrepanciesApi.getRecordDiscrepancies(selectedRecord.id)
      .then((items) => { if (!cancelled) setDiscrepancies(items); })
      .catch((err) => { if (!cancelled) toastError(err.message || 'Failed to load discrepancies'); })
      .finally(() => { if (!cancelled) setDetailLoading(false); });
    return () => { cancelled = true; };
  }, [selectedRecord?.id, toastError]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const handleApprove = async () => {
    if (!selectedRecord) return;
    setActionLoading(true);
    try {
      await reviewApi.approveRecord(selectedRecord.id, reviewNotes);
      success(`Parcel ${selectedRecord.khasra_number} approved successfully!`);
      setIsApproveOpen(false);
      setReviewNotes('');
      fetchQueue();
    } catch (err: any) {
      toastError(err?.message || 'Approval rejected');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRecord) return;
    if (!rejectionReason.trim() || rejectionReason.trim().length < 5) {
      toastError('Rejection justification must be at least 5 characters.');
      return;
    }

    setActionLoading(true);
    try {
      await reviewApi.rejectRecord(selectedRecord.id, rejectionReason, reviewNotes);
      success(`Parcel ${selectedRecord.khasra_number} rejected with recorded justification.`);
      setIsRejectOpen(false);
      setRejectionReason('');
      setReviewNotes('');
      fetchQueue();
    } catch (err: any) {
      toastError(err?.message || 'Rejection failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Workspace Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Officer Review Workspace
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
            Authoritative human-in-the-loop decision console for flagged records and parcel conflicts
          </p>
        </div>

        <button
          onClick={fetchQueue}
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
          <span>Refresh Queue ({queue.length})</span>
        </button>
      </div>

      {/* Split Workspace Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 1fr) minmax(480px, 1.8fr)',
          gap: '1.5rem',
          alignItems: 'start',
        }}
      >
        {/* Left: Queue List */}
        <div className="glass-panel" style={{ padding: '1.25rem', maxHeight: '780px', overflowY: 'auto' }}>
          <div
            style={{
              paddingBottom: '0.75rem',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              marginBottom: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
              Pending Tasks Queue
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                backgroundColor: 'rgba(244, 63, 94, 0.2)',
                color: '#fb7185',
                padding: '2px 8px',
                borderRadius: '9999px',
                fontWeight: 700,
              }}
            >
              {queue.length} Pending
            </span>
          </div>

          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
              Loading queue tasks...
            </div>
          ) : queue.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
              <CheckSquare size={32} color="#10b981" style={{ margin: '0 auto 0.5rem auto' }} />
              <div style={{ fontWeight: 600, color: '#f8fafc' }}>Review Queue Empty</div>
              <div style={{ fontSize: '0.78rem', marginTop: '2px' }}>
                No records are currently awaiting a review decision.
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {queue.map((rec) => {
                const isSelected = selectedRecord?.id === rec.id;
                return (
                  <div
                    key={rec.id}
                    onClick={() => selectRecord(rec)}
                    style={{
                      padding: '0.9rem',
                      borderRadius: '10px',
                      backgroundColor: isSelected
                        ? 'rgba(56, 189, 248, 0.12)'
                        : 'rgba(255, 255, 255, 0.02)',
                      border: isSelected
                        ? '1px solid rgba(56, 189, 248, 0.4)'
                        : '1px solid rgba(255, 255, 255, 0.06)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.9rem', color: isSelected ? '#38bdf8' : '#f8fafc' }}>
                        Parcel {rec.khasra_number}
                      </span>
                      <ConfidenceBadge score={rec.confidence_score} size="sm" />
                    </div>

                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '4px' }}>
                      Owner: {rec.owner_name || 'Unspecified'}
                    </div>

                    <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                      {rec.village}, {rec.district} • {rec.area_in_hectares} ha
                    </div>

                    <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                      <StatusBadge status={rec.status} size="sm" />
                      <StatusBadge status={rec.review_status} size="sm" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Record Examination & Decision Panel */}
        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          {selectedRecord ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#f8fafc' }}>
                      Khasra {selectedRecord.khasra_number}
                    </h3>
                    <StatusBadge status={selectedRecord.status} />
                    <StatusBadge status={selectedRecord.review_status} />
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '3px' }}>
                    Khata {selectedRecord.khata_number} • {selectedRecord.village}, {selectedRecord.tehsil}, {selectedRecord.district}
                  </p>
                </div>

                <button
                  onClick={() => navigate('record-detail', { recordId: selectedRecord.id })}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: '#38bdf8',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <span>Full Inspector View</span>
                  <ExternalLink size={13} />
                </button>
              </div>

              {/* Parcel Snapshot Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '0.75rem',
                  padding: '1rem',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  borderRadius: '10px',
                }}
              >
                <div>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Registered Owner</span>
                  <div style={{ fontWeight: 700, color: '#f1f5f9', fontSize: '0.9rem' }}>
                    {selectedRecord.owner_name || '—'}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Area (Hectares)</span>
                  <div style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.9rem', fontFamily: 'monospace' }}>
                    {selectedRecord.area_in_hectares} ha
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Confidence</span>
                  <div style={{ marginTop: '2px' }}>
                    <ConfidenceBadge score={selectedRecord.confidence_score} size="sm" />
                  </div>
                </div>
              </div>

              {/* Identified Discrepancies */}
              <div>
                <h4
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    color: '#e2e8f0',
                    marginBottom: '0.65rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <AlertTriangle size={16} color="#fb7185" />
                  <span>Detected Conflicts ({discrepancies.length})</span>
                </h4>

                {detailLoading ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: '#64748b' }}>
                    Checking cross-record comparisons...
                  </div>
                ) : discrepancies.length === 0 ? (
                  <div
                    style={{
                      padding: '1rem',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(16, 185, 129, 0.05)',
                      border: '1px solid rgba(16, 185, 129, 0.2)',
                      color: '#34d399',
                      fontSize: '0.82rem',
                    }}
                  >
                    Zero cross-record discrepancies detected. Record flagged due to validation rule triggers.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    {discrepancies.map((disc) => (
                      <div
                        key={disc.id}
                        style={{
                          padding: '0.85rem',
                          borderRadius: '8px',
                          backgroundColor: 'rgba(244, 63, 94, 0.08)',
                          border: '1px solid rgba(244, 63, 94, 0.25)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f8fafc' }}>
                            {disc.discrepancy_type}
                          </span>
                          <StatusBadge status={disc.severity} size="sm" />
                        </div>
                        <p style={{ fontSize: '0.8rem', color: '#fecdd3', marginTop: '4px' }}>
                          {disc.description}
                        </p>
                        {(disc.source_value || disc.conflicting_value) && (
                          <div
                            style={{
                              display: 'grid',
                              gridTemplateColumns: '1fr 1fr',
                              gap: '8px',
                              marginTop: '6px',
                              fontSize: '0.75rem',
                              color: '#cbd5e1',
                            }}
                          >
                            <div>Claimed: <strong>{disc.source_value}</strong></div>
                            <div>Registry: <strong style={{ color: '#fb7185' }}>{disc.conflicting_value}</strong></div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Review Governance Controls */}
              {canReview && (
                <div
                  style={{
                    paddingTop: '1.25rem',
                    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '1rem',
                  }}
                >
                  <button
                    onClick={() => setIsRejectOpen(true)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: 'rgba(244, 63, 94, 0.15)',
                      border: '1px solid rgba(244, 63, 94, 0.4)',
                      color: '#fb7185',
                      padding: '0.65rem 1.25rem',
                      borderRadius: '8px',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                    }}
                  >
                    <ThumbsDown size={15} />
                    <span>Reject Record</span>
                  </button>

                  <button
                    onClick={() => setIsApproveOpen(true)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: '#10b981',
                      border: 'none',
                      color: '#fff',
                      padding: '0.65rem 1.5rem',
                      borderRadius: '8px',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      boxShadow: '0 4px 12px rgba(16, 185, 129, 0.35)',
                    }}
                  >
                    <ThumbsUp size={15} />
                    <span>Approve Title Record</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '4rem', textAlign: 'center', color: '#64748b' }}>
              Select a land record from the queue on the left to examine.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Approve */}
      <Modal isOpen={isApproveOpen} onClose={() => setIsApproveOpen(false)} title="Statutory Title Approval">
        <div>
          <p style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '1rem' }}>
            Confirm approval of parcel <strong>{selectedRecord?.khasra_number}</strong>. This record will transition to VALIDATED.
          </p>

          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
            Officer Approval Commentary
          </label>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="e.g. Cross-verified against Tehsil physical mutation deed..."
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
              onClick={() => setIsApproveOpen(false)}
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
              onClick={handleApprove}
              disabled={actionLoading}
              style={{
                padding: '0.6rem 1.4rem',
                backgroundColor: '#10b981',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                fontWeight: 700,
                cursor: actionLoading ? 'not-allowed' : 'pointer',
              }}
            >
              {actionLoading ? 'Processing...' : 'Approve Record'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Reject */}
      <Modal isOpen={isRejectOpen} onClose={() => setIsRejectOpen(false)} title="Mandatory Rejection Justification">
        <div>
          <p style={{ fontSize: '0.88rem', color: '#fecdd3', marginBottom: '1rem' }}>
            Rejection requires mandatory statutory justification persisted to the audit logs.
          </p>

          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#fda4af', marginBottom: '0.4rem' }}>
            Statutory Rejection Reason (Required, min 5 chars) *
          </label>
          <textarea
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="e.g. Unreconciled ownership conflict with Khasra 104/2 in Bhopal registry..."
            rows={3}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(244, 63, 94, 0.4)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
            <button
              onClick={() => setIsRejectOpen(false)}
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
              onClick={handleReject}
              disabled={actionLoading || rejectionReason.trim().length < 5}
              style={{
                padding: '0.6rem 1.4rem',
                backgroundColor: '#f43f5e',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                fontWeight: 700,
                cursor: actionLoading || rejectionReason.trim().length < 5 ? 'not-allowed' : 'pointer',
                opacity: rejectionReason.trim().length < 5 ? 0.6 : 1,
              }}
            >
              {actionLoading ? 'Processing...' : 'Confirm Rejection'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
