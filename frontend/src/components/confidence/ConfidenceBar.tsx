import React from 'react';

interface ConfidenceBarProps {
  score: number;
  height?: number;
  showLabel?: boolean;
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({
  score,
  height = 8,
  showLabel = false,
}) => {
  const boundedScore = Math.max(0, Math.min(1, score));
  const percentage = Math.round(boundedScore * 100);

  let fillColor = '#10b981'; // High (Emerald)
  if (boundedScore < 0.60) {
    fillColor = '#f43f5e'; // Low (Rose)
  } else if (boundedScore < 0.85) {
    fillColor = '#f59e0b'; // Medium (Amber)
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
      <div
        style={{
          flex: 1,
          height: `${height}px`,
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          borderRadius: `${height / 2}px`,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            backgroundColor: fillColor,
            borderRadius: `${height / 2}px`,
            transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: `0 0 8px ${fillColor}66`,
          }}
        />
      </div>
      {showLabel && (
        <span
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: fillColor,
            minWidth: '36px',
            textAlign: 'right',
          }}
        >
          {percentage}%
        </span>
      )}
    </div>
  );
};
