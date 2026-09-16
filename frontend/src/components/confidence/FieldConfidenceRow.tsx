import React from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { FieldExtractionEvidence } from '../../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { ConfidenceBar } from './ConfidenceBar';

interface FieldConfidenceRowProps {
  label: string;
  fieldKey: string;
  evidence?: FieldExtractionEvidence;
  fallbackValue?: any;
  isCritical?: boolean;
}

export const FieldConfidenceRow: React.FC<FieldConfidenceRowProps> = ({
  label,
  evidence,
  fallbackValue,
  isCritical = false,
}) => {
  const rawValue = evidence?.value ?? fallbackValue ?? '—';
  const normalizedValue = evidence?.normalized_value;
  const confidence = evidence?.confidence ?? 1.0;
  const category = evidence?.category ?? 'HIGH';
  const isLow = category === 'LOW' || confidence < 0.60;
  const isWarning = isCritical && isLow;

  const displayRaw =
    typeof rawValue === 'object' && rawValue !== null
      ? JSON.stringify(rawValue)
      : String(rawValue);

  const displayNorm =
    normalizedValue !== undefined && normalizedValue !== null
      ? typeof normalizedValue === 'object'
        ? JSON.stringify(normalizedValue)
        : String(normalizedValue)
      : null;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(140px, 1.2fr) minmax(180px, 2fr) minmax(120px, 1.2fr) 90px',
        alignItems: 'center',
        gap: '1rem',
        padding: '0.85rem 1rem',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        backgroundColor: isWarning ? 'rgba(244, 63, 94, 0.06)' : 'transparent',
        transition: 'background-color 0.2s',
      }}
    >
      {/* Field Label & Warning Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {isWarning ? (
          <span title="Critical field with low confidence - manual verification required">
            <AlertTriangle size={16} color="#fb7185" />
          </span>
        ) : (
          <CheckCircle2 size={15} color="#34d399" style={{ opacity: 0.6 }} />
        )}
        <span
          style={{
            fontWeight: 600,
            fontSize: '0.88rem',
            color: isWarning ? '#fb7185' : '#e2e8f0',
          }}
        >
          {label}
        </span>
        {isCritical && (
          <span
            style={{
              fontSize: '0.68rem',
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              padding: '1px 6px',
              borderRadius: '4px',
              fontWeight: 500,
            }}
          >
            CRITICAL
          </span>
        )}
        {evidence?.source === 'ai_assistant' && (
          <span
            style={{
              fontSize: '0.65rem',
              background: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              padding: '1px 6px',
              borderRadius: '4px',
              fontWeight: 600,
            }}
            title="Extracted via optional Gemini AI interpretation - Requires verification"
          >
            AI-assisted suggestion
          </span>
        )}
      </div>

      {/* Extracted Values (Raw vs Normalized) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span
            style={{
              fontSize: '0.92rem',
              color: '#f8fafc',
              fontWeight: 500,
              fontFamily: 'monospace',
            }}
          >
            {displayRaw}
          </span>
          {displayNorm && displayNorm !== displayRaw && (
            <span
              style={{
                fontSize: '0.78rem',
                color: '#94a3b8',
                fontStyle: 'italic',
              }}
            >
              (norm: {displayNorm})
            </span>
          )}
        </div>
        {evidence?.evidence && (
          <span
            style={{
              fontSize: '0.72rem',
              color: '#64748b',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
            title={evidence.evidence}
          >
            snippet: "{evidence.evidence}"
          </span>
        )}
      </div>

      {/* Visual Confidence Bar */}
      <div style={{ minWidth: '100px' }}>
        <ConfidenceBar score={confidence} height={6} showLabel={false} />
      </div>

      {/* Confidence Pill Badge */}
      <div style={{ textAlign: 'right' }}>
        <ConfidenceBadge score={confidence} category={category} size="sm" />
      </div>
    </div>
  );
};
