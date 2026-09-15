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
        <div style={{ height: '36px', width: '260px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '8px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          {[...Array(9)].map((_, i) => (
            <div
              key={i}
              style={{
                height: '110px',
                backgroundColor: 'rgba(255,255,255,0.03)',
                borderRadius: '14px',
                border: '1px solid rgba(255,255,255,0.05)',
              }}
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
      bg: 'rgba(56, 189, 248, 0.1)',
      border: 'rgba(56, 189, 248, 0.25)',
      onClick: () => navigate('records'),
    },
    {
      title: 'Documents Processed',
      value: stats?.documents_processed ?? 0,
      icon: UploadCloud,
      color: '#818cf8',
      bg: 'rgba(129, 140, 248, 0.1)',
      border: 'rgba(129, 140, 248, 0.25)',
      onClick: () => navigate('upload'),
    },
    {
      title: 'Records Awaiting Review',
      value: stats?.records_awaiting_review ?? 0,
      icon: Clock,
      color: '#fbbf24',
      bg: 'rgba(251, 191, 36, 0.1)',
      border: 'rgba(251, 191, 36, 0.25)',
      onClick: () => navigate('review'),
    },
    {
      title: 'Validated Records',
      value: stats?.validated_records ?? 0,
      icon: CheckCircle2,
      color: '#34d399',
      bg: 'rgba(52, 211, 153, 0.1)',
      border: 'rgba(52, 211, 153, 0.25)',
      onClick: () => navigate('records'),
    },
    {
      title: 'Flagged Records',
      value: stats?.flagged_records ?? 0,
      icon: AlertTriangle,
      color: '#fb7185',
      bg: 'rgba(251, 113, 133, 0.1)',
      border: 'rgba(251, 113, 133, 0.25)',
      onClick: () => navigate('records'),
    },
    {
      title: 'Open Discrepancies',
      value: stats?.open_discrepancies ?? 0,
      icon: AlertTriangle,
      color: '#f97316',
      bg: 'rgba(249, 115, 22, 0.1)',
      border: 'rgba(249, 115, 22, 0.25)',
      onClick: () => navigate('discrepancies'),
    },
    {
      title: 'Low-Confidence Records',
      value: stats?.low_confidence_records ?? 0,
      icon: AlertTriangle,
      color: '#f43f5e',
      bg: 'rgba(244, 63, 94, 0.1)',
      border: 'rgba(244, 63, 94, 0.25)',
      onClick: () => navigate('records'),
    },
    {
      title: 'Approved Records',
      value: stats?.approved_records ?? 0,
      icon: ThumbsUp,
      color: '#10b981',
      bg: 'rgba(16, 185, 129, 0.1)',
      border: 'rgba(16, 185, 129, 0.25)',
      onClick: () => navigate('records'),
    },
    {
      title: 'Rejected Records',
      value: stats?.rejected_records ?? 0,
      icon: ThumbsDown,
      color: '#e11d48',
      bg: 'rgba(225, 29, 72, 0.1)',
      border: 'rgba(225, 29, 72, 0.25)',
      onClick: () => navigate('records'),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Land Intelligence Dashboard
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
            Real-time telemetry, automated OCR validation, and multi-record cross-examination
          </p>
        </div>

        <button
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
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
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* OCR & AI System Status Banner */}
      {ocrStatus && (
        <div
          className="glass-panel"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.5rem',
            borderLeft: '4px solid #10b981',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Cpu size={22} color="#10b981" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#fff' }}>
                  OCR Provider: {ocrStatus.provider_name}
                </span>
                <span
                  style={{
                    fontSize: '0.7rem',
                    background: 'rgba(16, 185, 129, 0.2)',
                    color: '#34d399',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 600,
                  }}
                >
                  ONLINE (100% OFFLINE OPERATIONAL)
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>
                Engine Version: {ocrStatus.engine_version || '5.5.3'} • Languages:{' '}
                {ocrStatus.supported_languages.join(', ')} • Selected:{' '}
                {ocrStatus.selected_engine}
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('system')}
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#38bdf8',
              padding: '0.45rem 0.85rem',
              borderRadius: '8px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Diagnostics View
          </button>
        </div>
      )}

      {/* 9 Metrics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="glass-panel"
              onClick={card.onClick}
              style={{
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                cursor: 'pointer',
                border: `1px solid ${card.border}`,
                backgroundColor: card.bg,
                transition: 'transform 0.2s, box-shadow 0.2s',
              }}
              onMouseOver={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-3px)';
              }}
              onMouseOut={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1' }}>
                  {card.title}
                </span>
                <Icon size={18} color={card.color} />
              </div>
              <div
                style={{
                  fontSize: '2rem',
                  fontWeight: 800,
                  color: card.color,
                  marginTop: '0.75rem',
                  letterSpacing: '-0.02em',
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
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
              Recent Ingested Documents
            </h3>
            <button
              onClick={() => navigate('upload')}
              style={{
                background: 'none',
                border: 'none',
                color: '#38bdf8',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {recentDocs.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <FileText size={18} color="#38bdf8" />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f1f5f9' }}>
                        {doc.file_name}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
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
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
                Flagged Records Requiring Review
              </h3>
              <span
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

            <button
              onClick={() => navigate('review')}
              style={{
                background: 'none',
                border: 'none',
                color: '#38bdf8',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {flaggedRecords.map((rec) => (
                <div
                  key={rec.id}
                  onClick={() => navigate('record-detail', { recordId: rec.id })}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    backgroundColor: 'rgba(244, 63, 94, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(244, 63, 94, 0.2)',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s',
                  }}
                  onMouseOver={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(244, 63, 94, 0.1)';
                  }}
                  onMouseOut={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(244, 63, 94, 0.05)';
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f1f5f9' }}>
                      Khasra {rec.khasra_number} • {rec.village}, {rec.district}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
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
