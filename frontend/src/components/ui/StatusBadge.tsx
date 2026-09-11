import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status ? status.toUpperCase() : 'UNKNOWN';

  const config: Record<
    string,
    { bg: string; border: string; text: string; dot: string; label?: string }
  > = {
    VALIDATED: {
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.35)',
      text: '#34d399',
      dot: '#10b981',
      label: 'VALIDATED',
    },
    APPROVED: {
      bg: 'rgba(16, 185, 129, 0.2)',
      border: 'rgba(16, 185, 129, 0.45)',
      text: '#34d399',
      dot: '#10b981',
      label: 'APPROVED',
    },
    RESOLVED: {
      bg: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.35)',
      text: '#34d399',
      dot: '#10b981',
      label: 'RESOLVED',
    },
    FLAGGED: {
      bg: 'rgba(244, 63, 94, 0.18)',
      border: 'rgba(244, 63, 94, 0.4)',
      text: '#fb7185',
      dot: '#f43f5e',
      label: 'FLAGGED',
    },
    REJECTED: {
      bg: 'rgba(244, 63, 94, 0.2)',
      border: 'rgba(244, 63, 94, 0.45)',
      text: '#fb7185',
      dot: '#f43f5e',
      label: 'REJECTED',
    },
    CRITICAL: {
      bg: 'rgba(244, 63, 94, 0.25)',
      border: 'rgba(244, 63, 94, 0.5)',
      text: '#fda4af',
      dot: '#f43f5e',
      label: 'CRITICAL',
    },
    HIGH: {
      bg: 'rgba(249, 115, 22, 0.2)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: '#fdba74',
      dot: '#f97316',
      label: 'HIGH',
    },
    PENDING_REVIEW: {
      bg: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.35)',
      text: '#fbbf24',
      dot: '#f59e0b',
      label: 'PENDING REVIEW',
    },
    OPEN: {
      bg: 'rgba(245, 158, 11, 0.18)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: '#fbbf24',
      dot: '#f59e0b',
      label: 'OPEN',
    },
    MEDIUM: {
      bg: 'rgba(234, 179, 8, 0.18)',
      border: 'rgba(234, 179, 8, 0.35)',
      text: '#fde047',
      dot: '#eab308',
      label: 'MEDIUM',
    },
    IN_REVIEW: {
      bg: 'rgba(168, 85, 247, 0.18)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: '#c084fc',
      dot: '#a855f7',
      label: 'IN REVIEW',
    },
    ACKNOWLEDGED: {
      bg: 'rgba(56, 189, 248, 0.15)',
      border: 'rgba(56, 189, 248, 0.35)',
      text: '#38bdf8',
      dot: '#0284c7',
      label: 'ACKNOWLEDGED',
    },
    EXTRACTED: {
      bg: 'rgba(56, 189, 248, 0.12)',
      border: 'rgba(56, 189, 248, 0.3)',
      text: '#38bdf8',
      dot: '#0ea5e9',
      label: 'EXTRACTED',
    },
    NORMALIZED: {
      bg: 'rgba(99, 102, 241, 0.15)',
      border: 'rgba(99, 102, 241, 0.35)',
      text: '#818cf8',
      dot: '#6366f1',
      label: 'NORMALIZED',
    },
    DISMISSED: {
      bg: 'rgba(148, 163, 184, 0.12)',
      border: 'rgba(148, 163, 184, 0.3)',
      text: '#94a3b8',
      dot: '#64748b',
      label: 'DISMISSED',
    },
    LOW: {
      bg: 'rgba(148, 163, 184, 0.12)',
      border: 'rgba(148, 163, 184, 0.3)',
      text: '#94a3b8',
      dot: '#64748b',
      label: 'LOW',
    },
    INFO: {
      bg: 'rgba(148, 163, 184, 0.1)',
      border: 'rgba(148, 163, 184, 0.25)',
      text: '#cbd5e1',
      dot: '#94a3b8',
      label: 'INFO',
    },
  };

  const current = config[normalized] || {
    bg: 'rgba(255, 255, 255, 0.08)',
    border: 'rgba(255, 255, 255, 0.15)',
    text: '#e2e8f0',
    dot: '#94a3b8',
    label: normalized,
  };

  const sizeStyles = {
    sm: { padding: '2px 8px', fontSize: '0.72rem' },
    md: { padding: '3px 10px', fontSize: '0.78rem' },
  }[size];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        backgroundColor: current.bg,
        border: `1px solid ${current.border}`,
        color: current.text,
        borderRadius: '9999px',
        fontWeight: 600,
        letterSpacing: '0.03em',
        whiteSpace: 'nowrap',
        ...sizeStyles,
      }}
    >
      <span
        style={{
          width: size === 'sm' ? 5 : 6,
          height: size === 'sm' ? 5 : 6,
          borderRadius: '50%',
          backgroundColor: current.dot,
        }}
      />
      <span>{current.label || normalized}</span>
    </span>
  );
};
