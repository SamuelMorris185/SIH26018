import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  FileText,
  AlertCircle,
  Plus,
} from 'lucide-react';
import { recordsApi, RecordFilterParams } from '../api/records';
import { useNavigation } from '../context/NavigationContext';
import { LandRecord } from '../types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';

export const RecordsList: React.FC = () => {
  const { navigate } = useNavigation();

  const [records, setRecords] = useState<LandRecord[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(10);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: RecordFilterParams = {
        page,
        limit,
      };

      if (statusFilter) {
        params.status = statusFilter;
      }
      if (searchQuery.trim()) {
        params.khasra_number = searchQuery.trim();
      }

      const response = await recordsApi.listRecords(params);
      setRecords(response.data || []);
      setTotal(response.total || 0);
    } catch (err: any) {
      setError(err?.message || 'Failed to load land records');
    } finally {
      setLoading(false);
    }
  }, [page, limit, statusFilter, searchQuery]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const totalPages = Math.ceil(total / limit) || 1;

  const filterPills = [
    { label: 'ALL RECORDS', value: '' },
    { label: 'VALIDATED', value: 'VALIDATED' },
    { label: 'FLAGGED', value: 'FLAGGED' },
    { label: 'EXTRACTED', value: 'EXTRACTED' },
    { label: 'REJECTED', value: 'REJECTED' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Title & Stats */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Land Records Registry
          </h2>
          <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '3px' }}>
            Official registry of extracted, normalized, and validated title records ({total} registered)
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={fetchRecords}
            className="btn btn-secondary"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => navigate('upload')}
            className="btn btn-primary"
          >
            <Plus size={16} />
            <span>Ingest New Record</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="bento-card"
        style={{
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '280px', maxWidth: '420px' }}>
            <Search
              size={18}
              color="#64748b"
              style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="text"
              placeholder="Search by Khasra Parcel No. (e.g. 104/2)..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              style={{ paddingLeft: '2.5rem' }}
            />
          </div>

          {/* Portfolio-inspired Rounded Pill Filter Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {filterPills.map((pill) => (
              <button
                key={pill.value}
                type="button"
                className={`pill-filter ${statusFilter === pill.value ? 'active' : ''}`}
                onClick={() => {
                  setStatusFilter(pill.value);
                  setPage(1);
                }}
              >
                <span className="font-mono">{pill.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            padding: '1rem',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '12px',
            color: '#f87171',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Records Table */}
      <div className="bento-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              <th>PARCEL ID (KHASRA/KHATA)</th>
              <th>OWNER / KHATEDAR</th>
              <th>LOCATION</th>
              <th>AREA</th>
              <th>CONFIDENCE</th>
              <th>VALIDATION</th>
              <th>REVIEW STATE</th>
              <th style={{ textAlign: 'right' }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  <td colSpan={8} style={{ padding: '1.25rem' }}>
                    <div style={{ height: '20px', borderRadius: '4px' }} className="skeleton-shimmer" />
                  </td>
                </tr>
              ))
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '3.5rem', textAlign: 'center', color: '#64748b' }}>
                  <FileText size={40} color="#334155" style={{ margin: '0 auto 0.75rem auto' }} />
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: '#94a3b8' }}>
                    No Land Records Found
                  </div>
                  <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                    {searchQuery ? 'Try adjusting your search criteria or filters.' : 'Upload a land document to begin digitization.'}
                  </div>
                </td>
              </tr>
            ) : (
              records.map((rec) => (
                <tr key={rec.id}>
                  <td style={{ padding: '1rem 1.25rem' }}>
                    <div className="font-mono" style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.9rem' }}>
                      Khasra {rec.khasra_number}
                    </div>
                    <div className="font-mono" style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Khata: {rec.khata_number}
                    </div>
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.88rem' }}>
                      {rec.owner_name || '—'}
                    </div>
                    {rec.co_owners && rec.co_owners.length > 0 && (
                      <div className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        +{rec.co_owners.length} joint holder(s)
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '1rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                    <div>{rec.village}</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {rec.tehsil}, {rec.district}
                    </div>
                  </td>
                  <td className="font-mono" style={{ padding: '1rem', fontSize: '0.88rem', color: '#f8fafc' }}>
                    {rec.area_in_hectares} ha
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <ConfidenceBadge score={rec.confidence_score} size="sm" />
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <StatusBadge status={rec.status} size="sm" />
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <StatusBadge status={rec.review_status} size="sm" />
                  </td>
                  <td style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>
                    <button
                      onClick={() => navigate('record-detail', { recordId: rec.id })}
                      className="btn btn-secondary"
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.78rem' }}
                    >
                      <Eye size={13} />
                      <span>Inspect Dossier</span>
                    </button>
                  </td>
                </tr>
              ))
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
              {total} records
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
