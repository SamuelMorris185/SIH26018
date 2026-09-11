import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  FileText,
  AlertCircle,
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Title & Stats */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
            Land Records Registry
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
            Official registry of extracted, normalized, and validated title records ({total} registered)
          </p>
        </div>

        <button
          onClick={fetchRecords}
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

      {/* Filter and Search Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '1rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
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
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem 0.6rem 2.4rem',
                backgroundColor: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: '#f8fafc',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={16} color="#64748b" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              style={{
                padding: '0.6rem 0.85rem',
                backgroundColor: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: '#cbd5e1',
                fontSize: '0.85rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="">All Validation Statuses</option>
              <option value="VALIDATED">VALIDATED</option>
              <option value="FLAGGED">FLAGGED</option>
              <option value="EXTRACTED">EXTRACTED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => navigate('upload')}
          style={{
            backgroundColor: '#0284c7',
            color: '#fff',
            border: 'none',
            padding: '0.6rem 1.1rem',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          + Ingest New Record
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            padding: '1rem',
            backgroundColor: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: '10px',
            color: '#fecdd3',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertCircle size={18} color="#f43f5e" />
          <span>{error}</span>
        </div>
      )}

      {/* Records Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                fontSize: '0.75rem',
                color: '#94a3b8',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              <th style={{ padding: '0.9rem 1.25rem' }}>Parcel ID (Khasra/Khata)</th>
              <th style={{ padding: '0.9rem 1rem' }}>Owner / Khatedar</th>
              <th style={{ padding: '0.9rem 1rem' }}>Location</th>
              <th style={{ padding: '0.9rem 1rem' }}>Area</th>
              <th style={{ padding: '0.9rem 1rem' }}>Confidence</th>
              <th style={{ padding: '0.9rem 1rem' }}>Validation</th>
              <th style={{ padding: '0.9rem 1rem' }}>Review State</th>
              <th style={{ padding: '0.9rem 1.25rem', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td colSpan={8} style={{ padding: '1.25rem' }}>
                    <div style={{ height: '20px', backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: '4px' }} />
                  </td>
                </tr>
              ))
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                  <FileText size={36} color="#334155" style={{ margin: '0 auto 0.75rem auto' }} />
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
                <tr
                  key={rec.id}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    transition: 'background-color 0.15s',
                  }}
                  onMouseOver={(e) => ((e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                  onMouseOut={(e) => ((e.currentTarget as HTMLElement).style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '1rem 1.25rem' }}>
                    <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.9rem' }}>
                      Khasra {rec.khasra_number}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Khata: {rec.khata_number}
                    </div>
                  </td>
                  <td style={{ padding: '1rem' }}>
                    <div style={{ fontWeight: 600, color: '#e2e8f0', fontSize: '0.88rem' }}>
                      {rec.owner_name || '—'}
                    </div>
                    {rec.co_owners && rec.co_owners.length > 0 && (
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
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
                  <td style={{ padding: '1rem', fontSize: '0.88rem', color: '#f8fafc', fontFamily: 'monospace' }}>
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
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        backgroundColor: 'rgba(56, 189, 248, 0.1)',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        color: '#38bdf8',
                        padding: '0.45rem 0.85rem',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                      onMouseOver={(e) => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = '#0284c7';
                        (e.currentTarget as HTMLElement).style.color = '#fff';
                      }}
                      onMouseOut={(e) => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'rgba(56, 189, 248, 0.1)';
                        (e.currentTarget as HTMLElement).style.color = '#38bdf8';
                      }}
                    >
                      <Eye size={13} />
                      <span>Inspect</span>
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
              backgroundColor: 'rgba(15, 23, 42, 0.5)',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Showing {Math.min((page - 1) * limit + 1, total)} to {Math.min(page * limit, total)} of{' '}
              {total} records
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
