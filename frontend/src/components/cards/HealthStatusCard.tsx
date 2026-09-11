import React, { useEffect, useState } from 'react';
import { healthService } from '../../services/healthService';
import { HealthStatus } from '../../types';
import { Activity, RefreshCw, CheckCircle2, AlertTriangle, Server, Database } from 'lucide-react';

export const HealthStatusCard: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await healthService.getHealth();
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backend server unreachable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
            <Activity size={20} color="var(--accent-emerald)" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>FastAPI System Verification</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Live REST API status & database connectivity check</p>
          </div>
        </div>

        <button
          onClick={fetchHealth}
          disabled={loading}
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.4rem 0.8rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.8rem',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-pulse-glow' : ''} />
          <span>{loading ? 'Polling...' : 'Refresh'}</span>
        </button>
      </div>

      {error ? (
        <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '1rem', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <AlertTriangle size={20} color="var(--accent-rose)" style={{ flexShrink: 0, marginTop: '0.1rem' }} />
          <div>
            <h4 style={{ fontSize: '0.9rem', color: 'var(--accent-rose)', fontWeight: 600 }}>Backend Unreachable</h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>{error}</p>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'block' }}>
              Ensure FastAPI backend is running via <code>python -m uvicorn app.main:app --port 8000</code>
            </span>
          </div>
        </div>
      ) : health ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <CheckCircle2 size={16} color="var(--accent-emerald)" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Status</span>
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-emerald)', textTransform: 'capitalize' }}>
              {health.status}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <Server size={16} color="var(--accent-blue)" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>FastAPI Engine</span>
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {health.services.backend.toUpperCase()}
            </div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <Database size={16} color="var(--accent-indigo)" />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>PostgreSQL Config</span>
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {health.services.database.toUpperCase()}
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
        <span>Environment: {health?.environment || 'development'}</span>
        <span>Last Checked: {lastChecked || 'N/A'}</span>
      </div>
    </div>
  );
};
