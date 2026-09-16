import React from 'react';
import { Shield, LogOut, User, Cpu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Header: React.FC = () => {
  const { user, role, logout, isAuthenticated } = useAuth();

  const roleStyles: Record<string, { bg: string; border: string; text: string; label: string }> = {
    ADMIN: {
      bg: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.4)',
      text: '#f87171',
      label: 'SYSTEM ADMIN',
    },
    REVIEWER: {
      bg: 'rgba(168, 85, 247, 0.15)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: '#c084fc',
      label: 'LAND REVIEWER',
    },
    OPERATOR: {
      bg: 'rgba(56, 189, 248, 0.15)',
      border: 'rgba(56, 189, 248, 0.4)',
      text: '#38bdf8',
      label: 'REVENUE OPERATOR',
    },
    VIEWER: {
      bg: 'rgba(148, 163, 184, 0.15)',
      border: 'rgba(148, 163, 184, 0.4)',
      text: '#cbd5e1',
      label: 'CITIZEN VIEWER',
    },
  };

  const currentRoleStyle = role ? roleStyles[role] || roleStyles.VIEWER : roleStyles.VIEWER;

  return (
    <header
      className="glass-panel"
      style={{
        borderRadius: 0,
        borderTop: 0,
        borderLeft: 0,
        borderRight: 0,
        padding: '0.85rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        zIndex: 50,
        backgroundColor: 'rgba(10, 13, 20, 0.85)',
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Brand & Portal Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div
          style={{
            background: 'linear-gradient(135deg, #0284c7, #4f46e5)',
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(56, 189, 248, 0.35)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
          }}
        >
          <Shield size={24} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1
              style={{
                fontSize: '1.25rem',
                fontWeight: 800,
                letterSpacing: '-0.02em',
                color: '#ffffff',
              }}
            >
              BHU-ABHILEKH
            </h1>
            <span
              style={{
                fontSize: '0.68rem',
                background: 'rgba(56, 189, 248, 0.12)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '2px 8px',
                borderRadius: '6px',
                fontWeight: 700,
                letterSpacing: '0.05em',
              }}
            >
              SIH26018
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Land record intelligence platform · OCR · validation · governance
          </p>
        </div>
      </div>

      {/* Right Controls & User Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        {/* Engine Status Chip */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '0.4rem 0.75rem',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            fontSize: '0.78rem',
            color: '#94a3b8',
          }}
        >
          <Cpu size={14} color="#10b981" />
          <span>SIH26018 Demo</span>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              backgroundColor: '#10b981',
              boxShadow: '0 0 6px #10b981',
            }}
          />
        </div>

        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* User Details & Role Badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}
              >
                <User size={18} color="#e2e8f0" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
                    {user.full_name}
                  </span>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      backgroundColor: currentRoleStyle.bg,
                      border: `1px solid ${currentRoleStyle.border}`,
                      color: currentRoleStyle.text,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {currentRoleStyle.label}
                  </span>
                </div>
                <span style={{ fontSize: '0.72rem', color: '#64748b' }}>{user.email}</span>
              </div>
            </div>

            {/* Logout Action */}
            <button
              onClick={logout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.25)',
                color: '#fb7185',
                padding: '0.45rem 0.85rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.backgroundColor = 'rgba(244, 63, 94, 0.2)';
                btn.style.color = '#fff';
              }}
              onMouseOut={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.backgroundColor = 'rgba(244, 63, 94, 0.1)';
                btn.style.color = '#fb7185';
              }}
              title="End session and log out"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
};
