import React from 'react';
import {
  LayoutDashboard,
  FileText,
  UploadCloud,
  CheckSquare,
  AlertTriangle,
  History,
  Activity,
  ChevronRight,
  Map,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNavigation } from '../../context/NavigationContext';
import { UserRole, ViewName } from '../../types';

interface NavItem {
  id: ViewName;
  label: string;
  icon: React.ElementType;
  allowedRoles: UserRole[];
  badge?: string;
}

export const Sidebar: React.FC = () => {
  const { role, hasRole } = useAuth();
  const { currentView, navigate } = useNavigation();

  const allNavItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Intelligence Dashboard',
      icon: LayoutDashboard,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
    {
      id: 'upload',
      label: 'Document Ingestion',
      icon: UploadCloud,
      allowedRoles: ['ADMIN', 'OPERATOR'],
    },
    {
      id: 'records',
      label: 'Land Records Explorer',
      icon: FileText,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
    {
      id: 'discrepancies',
      label: 'Discrepancy Hub',
      icon: AlertTriangle,
      allowedRoles: ['ADMIN', 'REVIEWER'],
    },
    {
      id: 'review',
      label: 'Review Workspace',
      icon: CheckSquare,
      allowedRoles: ['ADMIN', 'REVIEWER'],
    },
    {
      id: 'cadastral-map',
      label: 'Cadastral GIS Map',
      icon: Map,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
    {
      id: 'audit',
      label: 'Compliance Audit Logs',
      icon: History,
      allowedRoles: ['ADMIN'],
    },
    {
      id: 'system',
      label: 'System Diagnostics',
      icon: Activity,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
  ];

  const visibleItems = allNavItems.filter((item) => hasRole(...item.allowedRoles));

  return (
    <aside
      className="glass-panel"
      style={{
        width: '270px',
        borderRadius: 0,
        borderTop: 0,
        borderBottom: 0,
        borderLeft: 0,
        padding: '1.5rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        backgroundColor: 'rgba(10, 15, 26, 0.75)',
        minHeight: 'calc(100vh - 70px)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div
          style={{
            padding: '0 0.75rem 0.85rem 0.75rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            marginBottom: '0.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            className="font-mono"
            style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: '#64748b',
            }}
          >
            // WORKFLOW MODULES
          </span>
        </div>

        {visibleItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            currentView === item.id ||
            (item.id === 'records' && currentView === 'record-detail');

          return (
            <button
              key={item.id}
              onClick={() => navigate(item.id)}
              style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 0.95rem',
                borderRadius: '10px',
                border: isActive
                  ? '1px solid rgba(56, 189, 248, 0.35)'
                  : '1px solid transparent',
                background: isActive
                  ? 'linear-gradient(90deg, rgba(56, 189, 248, 0.14), rgba(56, 189, 248, 0.03))'
                  : 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.86rem',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.18s ease-in-out',
                boxShadow: isActive ? '0 0 15px rgba(56, 189, 248, 0.1)' : 'none',
              }}
              onMouseOver={(e) => {
                if (!isActive) {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                  btn.style.color = '#f8fafc';
                }
              }}
              onMouseOut={(e) => {
                if (!isActive) {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.style.backgroundColor = 'transparent';
                  btn.style.color = '#94a3b8';
                }
              }}
            >
              {/* Active Indicator Bar */}
              {isActive && (
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: '20%',
                    bottom: '20%',
                    width: '3px',
                    borderRadius: '0 4px 4px 0',
                    backgroundColor: '#38bdf8',
                    boxShadow: '0 0 8px #38bdf8',
                  }}
                />
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Icon size={18} color={isActive ? '#38bdf8' : '#64748b'} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight size={15} color="#38bdf8" />}
            </button>
          );
        })}
      </div>

      {/* Footer / Session Authorization Card */}
      <div
        className="glass-panel"
        style={{
          padding: '0.95rem',
          borderRadius: '12px',
          background: 'rgba(15, 23, 42, 0.5)',
          border: '1px solid rgba(255, 255, 255, 0.07)',
          fontSize: '0.75rem',
          color: '#64748b',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#94a3b8', marginBottom: '4px' }}>
          <ShieldCheck size={14} color="#10b981" />
          <span>Session Authorization</span>
        </div>
        <div>
          Level: <span className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{role || 'PUBLIC'}</span>
        </div>
        <div className="font-mono" style={{ fontSize: '0.68rem', marginTop: '6px', opacity: 0.75, color: '#64748b' }}>
          DILRMP Standards Compliant
        </div>
      </div>
    </aside>
  );
};
