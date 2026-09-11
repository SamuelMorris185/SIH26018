import React from 'react';
import { ConfidenceCategory } from '../../types';

interface ConfidenceBadgeProps {
  score?: number;
  category?: ConfidenceCategory | string;
  showPercent?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  score,
  category,
  showPercent = true,
  size = 'md',
}) => {
  let resolvedCategory: 'HIGH' | 'MEDIUM' | 'LOW' = 'HIGH';

  if (category) {
    const upper = category.toUpperCase();
    if (upper === 'HIGH' || upper === 'MEDIUM' || upper === 'LOW') {
      resolvedCategory = upper;
    }
  } else if (score !== undefined) {
    if (score >= 0.85) resolvedCategory = 'HIGH';
    else if (score >= 0.60) resolvedCategory = 'MEDIUM';
    else resolvedCategory = 'LOW';
  }

  const styles = {
    HIGH: {
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.35)',
      text: '#34d399',
      label: 'HIGH',
    },
    MEDIUM: {
      bg: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.35)',
      text: '#fbbf24',
      label: 'MEDIUM',
    },
    LOW: {
      bg: 'rgba(244, 63, 94, 0.15)',
      border: 'rgba(244, 63, 94, 0.35)',
      text: '#fb7185',
      label: 'LOW',
    },
  }[resolvedCategory];

  const sizeStyles = {
    sm: { padding: '2px 8px', fontSize: '0.72rem' },
    md: { padding: '4px 10px', fontSize: '0.8rem' },
    lg: { padding: '6px 14px', fontSize: '0.9rem' },
  }[size];

  const percentage = score !== undefined ? `${Math.round(score * 100)}%` : null;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        background: styles.bg,
        border: `1px solid ${styles.border}`,
        color: styles.text,
        borderRadius: '9999px',
        fontWeight: 600,
        letterSpacing: '0.02em',
        whiteSpace: 'nowrap',
        ...sizeStyles,
      }}
      title={score !== undefined ? `Confidence: ${(score * 100).toFixed(1)}%` : `Confidence: ${styles.label}`}
    >
      <span
        style={{
          width: size === 'sm' ? 6 : 8,
          height: size === 'sm' ? 6 : 8,
          borderRadius: '50%',
          backgroundColor: styles.text,
        }}
      />
      <span>{styles.label}</span>
      {showPercent && percentage && (
        <span style={{ opacity: 0.85, fontWeight: 500 }}>({percentage})</span>
      )}
    </span>
  );
};
