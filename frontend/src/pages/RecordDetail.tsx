import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  AlertTriangle,
  FileSearch,
  Layers,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Download,
  Eye,
  RefreshCw,
  Cpu,
  UserCheck,
  Sparkles,
} from 'lucide-react';
import { recordsApi } from '../api/records';
import { documentsApi } from '../api/documents';
import { discrepanciesApi } from '../api/discrepancies';
import { reviewApi } from '../api/review';
import { useNavigation } from '../context/NavigationContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  LandRecordDetail,
  ExtractionResult,
  ValidationCheck,
  Discrepancy,
  RecordComparison,
  ReviewDetail,
} from '../types';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';
import { FieldConfidenceRow } from '../components/confidence/FieldConfidenceRow';
import { CriticalConfidenceWarning } from '../components/confidence/CriticalConfidenceWarning';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Modal } from '../components/ui/Modal';
import { DocumentAnalysis } from '../components/document/DocumentAnalysis';
import { EnhancedPreview } from '../components/document/EnhancedPreview';

type DetailTab = 'fields' | 'preview' | 'validation' | 'discrepancies' | 'review' | 'summary';

export const RecordDetail: React.FC = () => {
  const { selectedRecordId, navigate, goBack } = useNavigation();
  const { role, hasRole } = useAuth();
  const { success, error: toastError } = useToast();

  const [record, setRecord] = useState<LandRecordDetail | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [validation, setValidation] = useState<ValidationCheck | null>(null);
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [comparisons, setComparisons] = useState<RecordComparison[]>([]);
  const [review, setReview] = useState<ReviewDetail | null>(null);

  const [activeTab, setActiveTab] = useState<DetailTab>('fields');
  const [loading, setLoading] = useState<boolean>(true);
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [previewMimeType, setPreviewMimeType] = useState<string>('');
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);

  // Review Modals
  const [isApproveOpen, setIsApproveOpen] = useState<boolean>(false);
  const [isRejectOpen, setIsRejectOpen] = useState<boolean>(false);
  const [isCompareRunning, setIsCompareRunning] = useState<boolean>(false);
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [isExportingReport, setIsExportingReport] = useState<boolean>(false);

  // Discrepancy Update Modal
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<Discrepancy | null>(null);
  const [discrepancyStatusTarget, setDiscrepancyStatusTarget] = useState<string>('RESOLVED');
  const [discrepancyNotes, setDiscrepancyNotes] = useState<string>('');

  const canReview = hasRole('ADMIN', 'REVIEWER');
  const requestId = useRef(0);

  const fetchRecordData = useCallback(async () => {
    const generation = ++requestId.current;
    if (!selectedRecordId) { setLoading(false); return; }
    setRecord(null);
    setLoading(true);

    try {
      const rec = await recordsApi.getRecord(selectedRecordId);
      if (generation !== requestId.current) return;
      setRecord(rec);

      // Fetch supporting details concurrently
      const [extData, valData, discData, compData, revData] = await Promise.all([
        recordsApi.getRecordExtraction(selectedRecordId).catch(() => null),
        recordsApi.getRecordValidation(selectedRecordId).catch(() => null),
        discrepanciesApi.getRecordDiscrepancies(selectedRecordId).catch(() => []),
        discrepanciesApi.getRecordComparisons(selectedRecordId).catch(() => []),
        reviewApi.getReviewStatus(selectedRecordId).catch(() => null),
      ]);

      if (generation !== requestId.current) return;

      setExtraction(extData);
      setValidation(valData || rec.latest_validation || null);
      setDiscrepancies(discData.length > 0 ? discData : rec.discrepancies || []);
      setComparisons(compData);
      setReview(revData);

    } catch (err: any) {
      if (generation !== requestId.current) return;
      toastError(err?.message || 'Failed to load record details');
    } finally {
      if (generation === requestId.current) setLoading(false);
    }
  }, [selectedRecordId, toastError]);

  useEffect(() => {
    fetchRecordData();
    return () => { requestId.current += 1; };
  }, [fetchRecordData]);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setPreviewBlobUrl(null);
    setPreviewMimeType('');
    if (!record?.document_id) return;
    setPreviewLoading(true);
    documentsApi.fetchDocumentBlob(record.document_id)
      .then(({ blob, mimeType }) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewBlobUrl(objectUrl);
        setPreviewMimeType(mimeType);
      })
      .catch((err) => { if (!cancelled) toastError(err.message || 'Preview unavailable'); })
      .finally(() => { if (!cancelled) setPreviewLoading(false); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [record?.document_id, toastError]);

  const handleApprove = async () => {
    if (!selectedRecordId) return;
    setActionLoading(true);
    try {
      const updated = await reviewApi.approveRecord(selectedRecordId, reviewNotes);
      setReview(updated);
      setIsApproveOpen(false);
      setReviewNotes('');
      success('Record review approved successfully.');
      fetchRecordData();
    } catch (err: any) {
      toastError(err?.message || 'Approval failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRecordId) return;
    if (!rejectionReason.trim() || rejectionReason.trim().length < 5) {
      toastError('Rejection justification must be at least 5 characters long.');
      return;
    }

    setActionLoading(true);
    try {
      const updated = await reviewApi.rejectRecord(selectedRecordId, rejectionReason, reviewNotes);
      setReview(updated);
      setIsRejectOpen(false);
      setRejectionReason('');
      setReviewNotes('');
      success('Record rejected with statutory justification.');
      fetchRecordData();
    } catch (err: any) {
      toastError(err?.message || 'Rejection failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerCompare = async () => {
    if (!selectedRecordId) return;
    setIsCompareRunning(true);
    try {
      const summary = await discrepanciesApi.compareRecord(selectedRecordId);
      success(
        `Cross-examination complete: ${summary.matched_records_count} matching parcel(s) checked, ${summary.total_discrepancies} discrepancy(s) found.`
      );
      fetchRecordData();
      setActiveTab('discrepancies');
    } catch (err: any) {
      toastError(err?.message || 'Comparison failed');
    } finally {
      setIsCompareRunning(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!selectedRecordId) return;
    setIsExportingReport(true);
    try {
      const { blob, filename } = await recordsApi.downloadVerificationReport(selectedRecordId);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      success('Verification report downloaded successfully.');
    } catch (err: any) {
      toastError(err?.message || 'Failed to generate verification report');
    } finally {
      setIsExportingReport(false);
    }
  };

  const handleUpdateDiscrepancyStatus = async () => {
    if (!selectedDiscrepancy) return;
    setActionLoading(true);
    try {
      await discrepanciesApi.updateDiscrepancyStatus(
        selectedDiscrepancy.id,
        discrepancyStatusTarget,
        discrepancyNotes
      );
      success(`Discrepancy status updated to ${discrepancyStatusTarget}.`);
      setSelectedDiscrepancy(null);
      setDiscrepancyNotes('');
      fetchRecordData();
    } catch (err: any) {
      toastError(err?.message || 'Discrepancy transition failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ height: '40px', width: '200px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '8px' }} />
        <div className="glass-panel" style={{ height: '300px' }} />
      </div>
    );
  }

  if (!record) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <AlertTriangle size={36} color="#fb7185" style={{ margin: '0 auto 1rem auto' }} />
        <h3 style={{ color: '#fff', fontSize: '1.2rem' }}>Land Record Not Found</h3>
        <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
          The requested record ID does not exist or you lack authorization to inspect it.
        </p>
        <button
          onClick={goBack}
          style={{
            marginTop: '1.5rem',
            padding: '0.6rem 1.25rem',
            backgroundColor: '#0284c7',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
          }}
        >
          Return to Registry
        </button>
      </div>
    );
  }

  const structuredFields = extraction?.structured_fields || {};
  const lowConfFields = extraction?.low_confidence_fields || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Breadcrumb & Actions Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={goBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#cbd5e1',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 className="font-mono" style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                Khasra Parcel {record.khasra_number}
              </h2>
              <StatusBadge status={record.status} />
              <StatusBadge status={record.review_status} />
            </div>
            <p className="font-mono" style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>
              Khata: {record.khata_number} • Village: {record.village}, {record.tehsil}, {record.district} • ID: {record.id}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={handleTriggerCompare}
            disabled={isCompareRunning}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: '#38bdf8',
              padding: '0.55rem 1rem',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: isCompareRunning ? 'not-allowed' : 'pointer',
            }}
          >
            <FileSearch size={15} />
            <span>{isCompareRunning ? 'Comparing...' : 'Run Cross-Document Match'}</span>
          </button>

          <button
            onClick={handleDownloadReport}
            disabled={isExportingReport}
            title="Export a system-generated Land Record Verification Report (PDF)"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'rgba(99, 102, 241, 0.12)',
              border: '1px solid rgba(99, 102, 241, 0.35)',
              color: '#818cf8',
              padding: '0.55rem 1rem',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: isExportingReport ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <Download size={15} />
            <span>{isExportingReport ? 'Generating PDF...' : 'Verification Report'}</span>
          </button>

          {canReview && (
            <>
              <button
                onClick={() => setIsApproveOpen(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#10b981',
                  border: 'none',
                  color: '#ffffff',
                  padding: '0.55rem 1.1rem',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)',
                }}
              >
                <ThumbsUp size={15} />
                <span>Approve</span>
              </button>

              <button
                onClick={() => setIsRejectOpen(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#f43f5e',
                  border: 'none',
                  color: '#ffffff',
                  padding: '0.55rem 1.1rem',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(244, 63, 94, 0.3)',
                }}
              >
                <ThumbsDown size={15} />
                <span>Reject</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Critical Low Confidence Alert */}
      <CriticalConfidenceWarning
        lowFields={lowConfFields}
        onOpenReview={() => setActiveTab('review')}
      />
      <DocumentAnalysis analysis={extraction?.analysis}/>
      {record.document_id && extraction?.analysis && <EnhancedPreview documentId={record.document_id} pages={extraction.analysis.pages.filter(p=>p.quality!==null).map(p=>p.page)}/>}

      {/* Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          paddingBottom: '0.25rem',
        }}
      >
        {[
          { id: 'fields', label: 'Extracted Fields & OCR', count: null },
          { id: 'preview', label: 'Original Document', count: null },
          { id: 'validation', label: 'Validation Rules', count: validation?.rule_results.length },
          { id: 'discrepancies', label: 'Cross-Record Conflicts', count: discrepancies.length },
          { id: 'review', label: 'Review Governance', count: null },
          { id: 'summary', label: 'Record Metadata', count: null },
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as DetailTab)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '0.65rem 1.1rem',
                border: 'none',
                borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                backgroundColor: isActive ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                borderRadius: '8px 8px 0 0',
                transition: 'all 0.15s',
              }}
            >
              <span>{tab.label}</span>
              {tab.count !== null && tab.count !== undefined && (
                <span
                  style={{
                    fontSize: '0.7rem',
                    padding: '1px 6px',
                    borderRadius: '9999px',
                    backgroundColor: tab.count > 0 ? (tab.id === 'discrepancies' ? 'rgba(244, 63, 94, 0.25)' : 'rgba(56, 189, 248, 0.2)') : 'rgba(255,255,255,0.06)',
                    color: tab.count > 0 ? (tab.id === 'discrepancies' ? '#fb7185' : '#38bdf8') : '#64748b',
                    fontWeight: 700,
                  }}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Extracted Fields & Confidence */}
      {activeTab === 'fields' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Header Metric Card */}
          <div
            className="glass-panel"
            style={{
              padding: '1.25rem 1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Cpu size={22} color="#38bdf8" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#fff' }}>
                  OCR Provider: {extraction?.provider || 'TESSERACT_OCR_V1'}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                  Deterministic field parser with Indian Revenue terminology normalization
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Overall Confidence</div>
                <div style={{ marginTop: '2px' }}>
                  <ConfidenceBadge score={record.confidence_score} size="md" />
                </div>
              </div>
            </div>
          </div>

          {/* AI Assistance Section */}
          <div
            className="glass-panel"
            style={{
              padding: '1.1rem 1.4rem',
              border: extraction?.ai_metadata?.ai_used
                ? '1px solid rgba(168, 85, 247, 0.35)'
                : '1px solid rgba(255, 255, 255, 0.08)',
              backgroundColor: extraction?.ai_metadata?.ai_used
                ? 'rgba(168, 85, 247, 0.04)'
                : 'rgba(255, 255, 255, 0.02)',
              borderRadius: '10px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    backgroundColor: extraction?.ai_metadata?.ai_used
                      ? 'rgba(168, 85, 247, 0.18)'
                      : 'rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Sparkles
                    size={18}
                    color={extraction?.ai_metadata?.ai_used ? '#c084fc' : '#94a3b8'}
                  />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>
                      AI Assistance
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        backgroundColor: extraction?.ai_metadata?.ai_used
                          ? 'rgba(168, 85, 247, 0.2)'
                          : 'rgba(148, 163, 184, 0.15)',
                        color: extraction?.ai_metadata?.ai_used ? '#c084fc' : '#94a3b8',
                        border: extraction?.ai_metadata?.ai_used
                          ? '1px solid rgba(168, 85, 247, 0.4)'
                          : '1px solid rgba(148, 163, 184, 0.2)',
                      }}
                    >
                      {extraction?.ai_metadata?.ai_used ? 'Active' : 'Disabled / Standby'}
                    </span>
                    {extraction?.ai_metadata?.ai_used && (
                      <span
                        style={{
                          fontSize: '0.68rem',
                          color: '#eab308',
                          backgroundColor: 'rgba(234, 179, 8, 0.1)',
                          border: '1px solid rgba(234, 179, 8, 0.25)',
                          padding: '2px 7px',
                          borderRadius: '4px',
                          fontWeight: 600,
                        }}
                      >
                        Requires verification
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>
                    {extraction?.ai_metadata?.ai_used
                      ? `Model: ${extraction.ai_metadata.model || 'gemini-3.8-flash'} • AI-assisted interpretation of noisy OCR`
                      : 'Deterministic pipeline only. Optional Gemini 3.8 Flash interpretation inactive.'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem', fontSize: '0.8rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>AI Suggestions</span>
                  <div style={{ fontWeight: 700, color: '#f8fafc' }}>
                    {extraction?.ai_metadata?.suggested_fields
                      ? Object.keys(extraction.ai_metadata.suggested_fields).length
                      : 0}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Conflicts Detected</span>
                  <div
                    style={{
                      fontWeight: 700,
                      color:
                        (extraction?.ai_metadata?.conflicts?.length || 0) > 0 ? '#fb7185' : '#10b981',
                    }}
                  >
                    {extraction?.ai_metadata?.conflicts?.length || 0}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Details when active */}
            {extraction?.ai_metadata?.ai_used && (
              <div
                style={{
                  marginTop: '0.85rem',
                  paddingTop: '0.75rem',
                  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  fontSize: '0.78rem',
                }}
              >
                {extraction.ai_metadata.summary && (
                  <div style={{ color: '#cbd5e1' }}>
                    <span style={{ color: '#94a3b8', fontWeight: 600 }}>Summary: </span>
                    {extraction.ai_metadata.summary}
                  </div>
                )}

                {extraction.ai_metadata.suggested_fields &&
                  Object.keys(extraction.ai_metadata.suggested_fields).length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                      <span style={{ color: '#94a3b8', fontWeight: 600 }}>AI-assisted fields:</span>
                      {Object.keys(extraction.ai_metadata.suggested_fields).map((fld) => (
                        <span
                          key={fld}
                          style={{
                            backgroundColor: 'rgba(168, 85, 247, 0.15)',
                            color: '#d8b4fe',
                            padding: '1px 7px',
                            borderRadius: '4px',
                            fontSize: '0.72rem',
                            fontWeight: 500,
                          }}
                        >
                          {fld}
                        </span>
                      ))}
                    </div>
                  )}

                {extraction.ai_metadata.conflicts && extraction.ai_metadata.conflicts.length > 0 && (
                  <div
                    style={{
                      backgroundColor: 'rgba(244, 63, 94, 0.08)',
                      border: '1px solid rgba(244, 63, 94, 0.25)',
                      borderRadius: '6px',
                      padding: '0.5rem 0.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div
                      style={{
                        color: '#fb7185',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                      }}
                    >
                      <AlertTriangle size={14} />
                      <span>Conflicts Requiring Review (Deterministic extraction preserved)</span>
                    </div>
                    {extraction.ai_metadata.conflicts.map((c, i) => (
                      <div key={i} style={{ color: '#e2e8f0', fontSize: '0.74rem' }}>
                        <strong>{c.field}</strong>: Deterministic="{String(c.deterministic_value)}" vs AI
                        suggestion="{String(c.ai_value)}"
                      </div>
                    ))}
                  </div>
                )}

                {extraction.ai_metadata.warnings && extraction.ai_metadata.warnings.length > 0 && (
                  <div style={{ color: '#fbbf24', fontSize: '0.74rem' }}>
                    <span style={{ fontWeight: 600 }}>Notices: </span>
                    {extraction.ai_metadata.warnings.join(' • ')}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Fields Table */}
          <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(140px, 1.2fr) minmax(180px, 2fr) minmax(120px, 1.2fr) 90px',
                padding: '0.75rem 1rem',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.72rem',
                color: '#64748b',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              <span>Field Name</span>
              <span>Extracted (Raw vs Normalized)</span>
              <span>Confidence Bar</span>
              <span style={{ textAlign: 'right' }}>Category</span>
            </div>

            <FieldConfidenceRow
              label="Khasra / Parcel No."
              fieldKey="khasra_number"
              evidence={structuredFields.khasra_number}
              fallbackValue={record.khasra_number}
              isCritical={true}
            />
            <FieldConfidenceRow
              label="Khata / Account No."
              fieldKey="khata_number"
              evidence={structuredFields.khata_number}
              fallbackValue={record.khata_number}
              isCritical={true}
            />
            <FieldConfidenceRow
              label="Owner / Khatedar"
              fieldKey="owner_name"
              evidence={structuredFields.owner_name}
              fallbackValue={record.owner_name}
              isCritical={true}
            />
            <FieldConfidenceRow
              label="Co-Owners / Joint"
              fieldKey="co_owners"
              evidence={structuredFields.co_owners}
              fallbackValue={record.co_owners}
            />
            <FieldConfidenceRow
              label="Area in Hectares"
              fieldKey="area_in_hectares"
              evidence={structuredFields.area_in_hectares}
              fallbackValue={record.area_in_hectares}
              isCritical={true}
            />
            <FieldConfidenceRow
              label="Land Classification"
              fieldKey="land_classification"
              evidence={structuredFields.land_classification}
              fallbackValue={record.land_classification}
            />
            <FieldConfidenceRow
              label="Village / Mauza"
              fieldKey="village"
              evidence={structuredFields.village}
              fallbackValue={record.village}
            />
            <FieldConfidenceRow
              label="Tehsil / Taluka"
              fieldKey="tehsil"
              evidence={structuredFields.tehsil}
              fallbackValue={record.tehsil}
            />
            <FieldConfidenceRow
              label="District / Jila"
              fieldKey="district"
              evidence={structuredFields.district}
              fallbackValue={record.district}
            />
            <FieldConfidenceRow
              label="State / Rajya"
              fieldKey="state"
              evidence={structuredFields.state}
              fallbackValue={record.state}
            />
            <FieldConfidenceRow
              label="Patta Number"
              fieldKey="patta_number"
              evidence={structuredFields.patta_number}
              fallbackValue={record.patta_number}
            />
            <FieldConfidenceRow
              label="Registration Number"
              fieldKey="registration_number"
              evidence={structuredFields.registration_number}
              fallbackValue={record.registration_number}
            />
            <FieldConfidenceRow
              label="Mutation Number"
              fieldKey="mutation_number"
              evidence={structuredFields.mutation_number}
              fallbackValue={record.mutation_number}
            />
          </div>

          {/* Raw OCR Text Viewer */}
          {extraction?.raw_text && (
            <div className="glass-panel" style={{ padding: '1.25rem' }}>
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                Raw OCR Text Stream
              </div>
              <pre
                style={{
                  backgroundColor: 'rgba(0,0,0,0.4)',
                  padding: '1rem',
                  borderRadius: '8px',
                  color: '#94a3b8',
                  fontSize: '0.78rem',
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '220px',
                  overflowY: 'auto',
                }}
              >
                {extraction.raw_text}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Original Document Preview */}
      {activeTab === 'preview' && (
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                Original Document Binary Stream
              </h3>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Secure inline document rendering via authorized streaming gateway
              </p>
            </div>

            {previewBlobUrl && (
              <a
                href={previewBlobUrl}
                download={`document_${record.document_id || record.id}.pdf`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'rgba(56, 189, 248, 0.12)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#38bdf8',
                  padding: '0.45rem 0.9rem',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                <Download size={14} />
                <span>Download Original</span>
              </a>
            )}
          </div>

          {previewLoading ? (
            <div style={{ padding: '4rem', textAlign: 'center', color: '#94a3b8' }}>
              <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 0.75rem auto' }} />
              <div>Streaming document binary...</div>
            </div>
          ) : previewBlobUrl ? (
            previewMimeType.includes('pdf') ? (
              <iframe
                src={previewBlobUrl}
                title="Document PDF Preview"
                style={{
                  width: '100%',
                  height: '650px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px',
                  backgroundColor: '#ffffff',
                }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem' }}>
                <img
                  src={previewBlobUrl}
                  alt="Scanned Land Document"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '650px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                />
              </div>
            )
          ) : (
            <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
              <FileText size={36} style={{ margin: '0 auto 0.5rem auto' }} />
              <div>No source document binary associated with this record.</div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Validation Rules Engine Report */}
      {activeTab === 'validation' && (
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                Statutory Rule Validation Report
              </h3>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Engine evaluation across mandatory fields, parcel formats, area sanity, and confidence
              </p>
            </div>
            {validation && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Status:</span>
                <StatusBadge status={validation.status} />
              </div>
            )}
          </div>

          {!validation || validation.rule_results.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
              No validation audits generated yet for this record.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {validation.rule_results.map((rule, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '1rem',
                    padding: '0.9rem 1.1rem',
                    borderRadius: '10px',
                    backgroundColor: rule.passed ? 'rgba(16, 185, 129, 0.05)' : 'rgba(244, 63, 94, 0.08)',
                    border: `1px solid ${rule.passed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.3)'}`,
                  }}
                >
                  <div style={{ marginTop: '2px' }}>
                    {rule.passed ? (
                      <CheckCircle2 size={18} color="#10b981" />
                    ) : (
                      <AlertTriangle size={18} color="#f43f5e" />
                    )}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>
                        {rule.rule_name}
                      </span>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '4px',
                          backgroundColor: rule.passed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                          color: rule.passed ? '#34d399' : '#fb7185',
                        }}
                      >
                        {rule.passed ? 'PASSED' : rule.severity}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '3px' }}>
                      {rule.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Cross-Record Comparisons & Discrepancies */}
      {activeTab === 'discrepancies' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div
            className="glass-panel"
            style={{
              padding: '1.25rem 1.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                Multi-Record Parcel Cross-Examination
              </h3>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Detects ownership mismatches, survey conflicts, and duplicate claims across revenue records
              </p>
            </div>
            <button
              onClick={handleTriggerCompare}
              disabled={isCompareRunning}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#0284c7',
                border: 'none',
                color: '#fff',
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: isCompareRunning ? 'not-allowed' : 'pointer',
              }}
            >
              <FileSearch size={15} />
              <span>{isCompareRunning ? 'Analyzing...' : 'Re-Run Cross-Match'}</span>
            </button>
          </div>

          {discrepancies.length === 0 ? (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
              <CheckCircle2 size={36} color="#10b981" style={{ margin: '0 auto 0.75rem auto' }} />
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc' }}>
                Zero Discrepancies Detected
              </div>
              <p style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                No title mismatches or parcel conflicts were found against existing registry entries.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {discrepancies.map((disc) => (
                <div
                  key={disc.id}
                  className="glass-panel"
                  style={{
                    padding: '1.25rem',
                    borderLeft: `4px solid ${
                      disc.severity === 'CRITICAL'
                        ? '#f43f5e'
                        : disc.severity === 'HIGH'
                        ? '#f97316'
                        : '#fbbf24'
                    }`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 800, fontSize: '0.95rem', color: '#f8fafc' }}>
                        {disc.discrepancy_type}
                      </span>
                      <StatusBadge status={disc.severity} size="sm" />
                      <StatusBadge status={disc.status} size="sm" />
                    </div>

                    {canReview && (
                      <button
                        onClick={() => {
                          setSelectedDiscrepancy(disc);
                          setDiscrepancyStatusTarget(disc.status === 'OPEN' ? 'RESOLVED' : 'ACKNOWLEDGED');
                        }}
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          backgroundColor: 'rgba(255, 255, 255, 0.06)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          color: '#38bdf8',
                          padding: '0.35rem 0.75rem',
                          borderRadius: '6px',
                          cursor: 'pointer',
                        }}
                      >
                        Update Status
                      </button>
                    )}
                  </div>

                  <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.6rem' }}>
                    {disc.description}
                  </p>

                  {(disc.source_value || disc.conflicting_value) && (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '1rem',
                        marginTop: '0.85rem',
                        padding: '0.75rem',
                        backgroundColor: 'rgba(0,0,0,0.3)',
                        borderRadius: '8px',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div>
                        <span style={{ color: '#94a3b8', fontSize: '0.72rem', display: 'block' }}>
                          Current Record Value:
                        </span>
                        <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                          {disc.source_value || '—'}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: '#94a3b8', fontSize: '0.72rem', display: 'block' }}>
                          Conflicting Registry Value:
                        </span>
                        <span style={{ color: '#fb7185', fontWeight: 600 }}>
                          {disc.conflicting_value || '—'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Review Governance */}
      {activeTab === 'review' && (
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
                Human Review & Audit Trail
              </h3>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Statutory approvals, rejection justifications, and review lifecycle history
              </p>
            </div>
            <StatusBadge status={review?.review_status || record.review_status} />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem',
            }}
          >
            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Reviewed By</div>
              <div style={{ fontWeight: 600, color: '#f1f5f9', marginTop: '2px' }}>
                {review?.reviewed_by || 'Pending Assignment'}
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Reviewed At</div>
              <div style={{ fontWeight: 600, color: '#f1f5f9', marginTop: '2px' }}>
                {review?.reviewed_at ? new Date(review.reviewed_at).toLocaleString() : '—'}
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Review Comments</div>
              <div style={{ fontWeight: 600, color: '#f1f5f9', marginTop: '2px' }}>
                {review?.review_notes || 'None recorded'}
              </div>
            </div>
          </div>

          {review?.rejection_reason && (
            <div
              style={{
                padding: '1rem',
                backgroundColor: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '8px',
                marginBottom: '1.5rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fb7185' }}>
                STATUTORY REJECTION JUSTIFICATION:
              </div>
              <div style={{ fontSize: '0.85rem', color: '#fecdd3', marginTop: '4px' }}>
                {review.rejection_reason}
              </div>
            </div>
          )}

          {/* Review Actions if Reviewer */}
          {canReview && (
            <div
              style={{
                paddingTop: '1.25rem',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                gap: '1rem',
                justifyContent: 'flex-end',
              }}
            >
              <button
                onClick={() => setIsApproveOpen(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#10b981',
                  color: '#fff',
                  border: 'none',
                  padding: '0.65rem 1.4rem',
                  borderRadius: '8px',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                <ThumbsUp size={16} />
                <span>Approve Land Record</span>
              </button>

              <button
                onClick={() => setIsRejectOpen(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#f43f5e',
                  color: '#fff',
                  border: 'none',
                  padding: '0.65rem 1.4rem',
                  borderRadius: '8px',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                <ThumbsDown size={16} />
                <span>Reject Land Record</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Record Metadata Summary */}
      {activeTab === 'summary' && (
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1rem' }}>
            System Metadata & Timestamps
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
            <div style={{ padding: '0.85rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Record UUID</span>
              <div style={{ fontSize: '0.82rem', fontFamily: 'monospace', color: '#38bdf8', marginTop: '2px' }}>
                {record.id}
              </div>
            </div>

            <div style={{ padding: '0.85rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Source Document UUID</span>
              <div style={{ fontSize: '0.82rem', fontFamily: 'monospace', color: '#e2e8f0', marginTop: '2px' }}>
                {record.document_id || 'Direct Entry'}
              </div>
            </div>

            <div style={{ padding: '0.85rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Ingestion Created Timestamp</span>
              <div style={{ fontSize: '0.85rem', color: '#e2e8f0', marginTop: '2px' }}>
                {new Date(record.created_at).toLocaleString()}
              </div>
            </div>

            <div style={{ padding: '0.85rem', backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Last Updated Timestamp</span>
              <div style={{ fontSize: '0.85rem', color: '#e2e8f0', marginTop: '2px' }}>
                {record.updated_at ? new Date(record.updated_at).toLocaleString() : '—'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Approve Record */}
      <Modal isOpen={isApproveOpen} onClose={() => setIsApproveOpen(false)} title="Confirm Statutory Approval">
        <div>
          <p style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '1rem' }}>
            Are you sure you want to approve this land title record? This will mark the record as{' '}
            <strong style={{ color: '#34d399' }}>VALIDATED</strong> and approve its extracted parcel parameters.
          </p>

          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
            Optional Approval Commentary
          </label>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="e.g. Verified against Patwari register volume 4..."
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
              resize: 'vertical',
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
              {actionLoading ? 'Processing...' : 'Confirm Approval'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal: Reject Record */}
      <Modal isOpen={isRejectOpen} onClose={() => setIsRejectOpen(false)} title="Mandatory Statutory Rejection">
        <div>
          <p style={{ fontSize: '0.88rem', color: '#fecdd3', marginBottom: '1rem' }}>
            Rejecting a land title record requires a mandatory justification entered into the permanent audit trail.
          </p>

          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#fda4af', marginBottom: '0.4rem' }}>
            Statutory Rejection Reason (Required, min 5 chars) *
          </label>
          <textarea
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="e.g. Area mismatch of 0.4 ha exceeds legal tolerance; fraudulent mutation..."
            rows={3}
            required
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(244, 63, 94, 0.4)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none',
              resize: 'vertical',
            }}
          />

          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', margin: '0.75rem 0 0.4rem 0' }}>
            Additional Administrative Notes (Optional)
          </label>
          <input
            type="text"
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="e.g. Forwarded to Sub-Divisional Magistrate..."
            style={{
              width: '100%',
              padding: '0.65rem 0.75rem',
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

      {/* Modal: Update Discrepancy Status */}
      {selectedDiscrepancy && (
        <Modal
          isOpen={!!selectedDiscrepancy}
          onClose={() => setSelectedDiscrepancy(null)}
          title={`Update Discrepancy: ${selectedDiscrepancy.discrepancy_type}`}
        >
          <div>
            <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '1rem' }}>
              {selectedDiscrepancy.description}
            </div>

            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
              Target Resolution Status
            </label>
            <select
              value={discrepancyStatusTarget}
              onChange={(e) => setDiscrepancyStatusTarget(e.target.value)}
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
              <option value="ACKNOWLEDGED">ACKNOWLEDGED (Mark for investigation)</option>
              <option value="RESOLVED">RESOLVED (Discrepancy reconciled)</option>
              <option value="DISMISSED">DISMISSED (Deemed false positive / acceptable variation)</option>
              <option value="OPEN">OPEN (Re-open for review)</option>
            </select>

            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem' }}>
              Resolution Notes
            </label>
            <textarea
              value={discrepancyNotes}
              onChange={(e) => setDiscrepancyNotes(e.target.value)}
              placeholder="e.g. Reconciled with mutation deed dated 12/03/2024..."
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
                onClick={handleUpdateDiscrepancyStatus}
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
                {actionLoading ? 'Updating...' : 'Update Status'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
