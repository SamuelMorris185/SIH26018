import React from 'react';
import { AlertTriangle, ArrowRight } from 'lucide-react';

interface CriticalConfidenceWarningProps {
  lowFields: string[];
  onOpenReview?: () => void;
}

export const CriticalConfidenceWarning: React.FC<CriticalConfidenceWarningProps> = ({
  lowFields,
  onOpenReview,
}) => {
  if (!lowFields || lowFields.length === 0) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem 1.25rem',
        backgroundColor: 'rgba(244, 63, 94, 0.12)',
        border: '1px solid rgba(244, 63, 94, 0.35)',
        borderRadius: '12px',
        color: '#fecdd3',
        marginBottom: '1.25rem',
        boxShadow: '0 4px 12px rgba(244, 63, 94, 0.15)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
        <AlertTriangle size={22} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#fff' }}>
            Low Confidence Detected on Critical Land Fields
          </div>
          <div style={{ fontSize: '0.82rem', marginTop: '3px', color: '#fda4af' }}>
            Automated OCR confidence fell below the safety threshold (60%) for:{' '}
            <strong>{lowFields.join(', ')}</strong>. This record has been automatically{' '}
            <span style={{ color: '#fff', fontWeight: 600 }}>FLAGGED</span> and requires mandatory
            human verification.
          </div>
        </div>
      </div>

      {onOpenReview && (
        <button
          onClick={onOpenReview}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#f43f5e',
            color: '#fff',
            border: 'none',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: 'pointer',
            flexShrink: 0,
            transition: 'background-color 0.2s',
          }}
          onMouseOver={(e) => ((e.currentTarget as HTMLButtonElement).style.backgroundColor = '#e11d48')}
          onMouseOut={(e) => ((e.currentTarget as HTMLButtonElement).style.backgroundColor = '#f43f5e')}
        >
          Review Workspace
          <ArrowRight size={15} />
        </button>
      )}
    </div>
  );
};
