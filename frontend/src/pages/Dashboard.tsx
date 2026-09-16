import React, { useEffect, useState } from 'react';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Cpu,
  Layers,
  ArrowUpRight,
  RefreshCw,
  Activity,
  ShieldAlert,
} from 'lucide-react';
import { systemApi } from '../api/system';
import { documentsApi } from '../api/documents';
import { recordsApi } from '../api/records';
import { discrepanciesApi } from '../api/discrepancies';
import { useNavigation } from '../context/NavigationContext';
import { useAuth } from '../context/AuthContext';
import { DashboardStats, OCRStatus, Document, LandRecord, Discrepancy } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';

export const Dashboard: React.FC = () => {
  const { navigate } = useNavigation();
  const { role } = useAuth();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [ocrStatus, setOcrStatus] = useState<OCRStatus | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [flaggedRecords, setFlaggedRecords] = useState<LandRecord[]>([]);
  const [openDiscrepancies, setOpenDiscrepancies] = useState<Discrepancy[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const [statsData, ocrData, docsData, flaggedData, discData] = await Promise.all([
        systemApi.getDashboardStats(),
        systemApi.getOCRStatus(),
        documentsApi.listDocuments({ limit: 5 }),
        recordsApi.listRecords({ status: 'FLAGGED', limit: 5 }),
        discrepanciesApi.listDiscrepancies({ status: 'OPEN', limit: 5 }),
      ]);

      if (statsData) setStats(statsData);
      if (ocrData) setOcrStatus(ocrData);
      setRecentDocs(docsData.data || []);
      setFlaggedRecords(flaggedData.data || []);
      setOpenDiscrepancies(discData.data || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ height: '32px', width: '240px', borderRadius: '8px' }} className="skeleton-shimmer" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          {[...Array(9)].map((_, i) => (
            <div
              key={i}
              style={{ height: '110px', borderRadius: '16px' }}
              className="glass-panel skeleton-shimmer"
            />
          ))}
        </div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Land Records',
      value: stats?.total_records ?? 0,
      icon: Layers,
      color: '#38bdf8',
      onClick: () => navigate('records'),
    },
    {
      title: 'Documents Processed',
      value: stats?.documents_processed ?? 0,
      icon: UploadCloud,
      color: '#818cf8',
      onClick: () => navigate('upload'),
    },
    {
      title: 'Awaiting Review',
      value: stats?.records_awaiting_review ?? 0,
      icon: Clock,
      color: '#fbbf24',
      onClick: () => navigate('review'),
    },
    {
      title: 'Validated Records',
      value: stats?.validated_records ?? 0,
      icon: CheckCircle2,
      color: '#34d399',
      onClick: () => navigate('records'),
    },
    {
      title: 'Flagged Records',
      value: stats?.flagged_records ?? 0,
      icon: AlertTriangle,
      color: '#fb7185',
      onClick: () => navigate('records'),
    },
    {
      title: 'Open Discrepancies',
      value: stats?.open_discrepancies ?? 0,
      icon: ShieldAlert,
      color: '#f97316',
      onClick: () => navigate('discrepancies'),
    },
    {
      title: 'Low-Confidence Records',
      value: stats?.low_confidence_records ?? 0,
      icon: AlertTriangle,
      color: '#f43f5e',
      onClick: () => navigate('records'),
    },
    {
      title: 'Approved Records',
      value: stats?.approved_records ?? 0,
      icon: ThumbsUp,
      color: '#10b981',
      onClick: () => navigate('records'),
    },
    {
      title: 'Rejected Records',
      value: stats?.rejected_records ?? 0,
      icon: ThumbsDown,
      color: '#e11d48',
      onClick: () => navigate('records'),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Land Intelligence Dashboard
          </h2>
          <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '3px' }}>
            Real-time telemetry, automated OCR validation, and multi-record cross-examination
          </p>
        </div>

        <button
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
          className="btn btn-secondary"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* OCR & AI System Status Banner */}
      {ocrStatus && (
        <div
          className="bento-card"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.1rem 1.5rem',
            borderLeft: '4px solid #10b981',
            background: 'rgba(15, 23, 42, 0.8)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Cpu size={22} color="#10b981" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                  OCR Provider: {ocrStatus.provider_name}
                </span>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.68rem',
                    background: 'rgba(16, 185, 129, 0.18)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.35)',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    fontWeight: 700,
                  }}
                >
                  ONLINE (100% OFFLINE OPERATIONAL)
                </span>
              </div>
              <div className="font-mono" style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '3px' }}>
                Engine Version: {ocrStatus.engine_version || '5.5.3'} • Languages:{' '}
                {ocrStatus.supported_languages.join(', ')} • Selected:{' '}
                {ocrStatus.selected_engine}
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('system')}
            className="btn btn-ghost"
            style={{ fontSize: '0.8rem' }}
          >
            <Activity size={14} color="#38bdf8" />
            <span>Diagnostics</span>
          </button>
        </div>
      )}

      {/* Bento Grid Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.1rem' }}>
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="bento-card"
              onClick={card.onClick}
              style={{
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                padding: '1.25rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {card.title}
                </span>
                <Icon size={18} color={card.color} />
              </div>
              <div
                style={{
                  fontSize: '2.1rem',
                  fontWeight: 800,
                  color: card.color,
                  marginTop: '0.85rem',
                  letterSpacing: '-0.03em',
                  fontFamily: 'var(--font-display)',
                }}
              >
                {card.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* 2-Column Activity Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '1.5rem' }}>
        {/* Recent Ingested Documents */}
        <div className="bento-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.1rem' }}>
            <div>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                // RECENT INGESTION
              </span>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
                Document Ingestion Stream
              </h3>
            </div>
            <button
              onClick={() => navigate('upload')}
              className="btn btn-ghost"
              style={{ fontSize: '0.78rem', color: '#38bdf8' }}
            >
              <span>Ingest New</span>
              <ArrowUpRight size={14} />
            </button>
          </div>

          {recentDocs.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              No document uploads recorded yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {recentDocs.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <FileText size={18} color="#38bdf8" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.86rem', color: '#f1f5f9' }}>
                        {doc.file_name}
                      </div>
                      <div className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        {doc.doc_type} • {(doc.file_size_bytes / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={doc.status} size="sm" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action Required: Flagged Records */}
        <div className="bento-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.1rem' }}>
            <div>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: '#fb7185', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                // DISCREPANCY AUDIT
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
                  Flagged Records
                </h3>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.7rem',
                    background: 'rgba(244, 63, 94, 0.2)',
                    color: '#fb7185',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    fontWeight: 700,
                  }}
                >
                  {flaggedRecords.length}
                </span>
              </div>
            </div>

            <button
              onClick={() => navigate('review')}
              className="btn btn-ghost"
              style={{ fontSize: '0.78rem', color: '#38bdf8' }}
            >
              <span>Review Workspace</span>
              <ArrowUpRight size={14} />
            </button>
          </div>

          {flaggedRecords.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              Zero flagged records currently pending. All records clear!
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {flaggedRecords.map((rec) => (
                <div
                  key={rec.id}
                  onClick={() => navigate('record-detail', { recordId: rec.id })}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'rgba(244, 63, 94, 0.04)',
                    borderRadius: '10px',
                    border: '1px solid rgba(244, 63, 94, 0.18)',
                    cursor: 'pointer',
                    transition: 'all 0.18s ease',
                  }}
                  onMouseOver={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(244, 63, 94, 0.08)';
                    (e.currentTarget as HTMLElement).style.borderColor = 'rgba(244, 63, 94, 0.35)';
                  }}
                  onMouseOut={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(244, 63, 94, 0.04)';
                    (e.currentTarget as HTMLElement).style.borderColor = 'rgba(244, 63, 94, 0.18)';
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.86rem', color: '#f1f5f9' }}>
                      Khasra {rec.khasra_number} • {rec.village}, {rec.district}
                    </div>
                    <div className="font-mono" style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                      Owner: {rec.owner_name || 'Unspecified'} • {rec.area_in_hectares} ha
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ConfidenceBadge score={rec.confidence_score} size="sm" />
                    <StatusBadge status={rec.status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
