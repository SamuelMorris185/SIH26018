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
      id: 'records',
      label: 'Land Records Explorer',
      icon: FileText,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
    {
      id: 'cadastral-map',
      label: 'Cadastral GIS Map',
      icon: Map,
      allowedRoles: ['ADMIN', 'OPERATOR', 'REVIEWER', 'VIEWER'],
    },
    {
      id: 'upload',

      label: 'Document Ingestion',
      icon: UploadCloud,
      allowedRoles: ['ADMIN', 'OPERATOR'],
    },
    {
      id: 'review',
      label: 'Review Workspace',
      icon: CheckSquare,
      allowedRoles: ['ADMIN', 'REVIEWER'],
    },
    {
      id: 'discrepancies',
      label: 'Discrepancy Hub',
      icon: AlertTriangle,
      allowedRoles: ['ADMIN', 'REVIEWER'],
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
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        minHeight: 'calc(100vh - 70px)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div
          style={{
            padding: '0 0.75rem 0.85rem 0.75rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            marginBottom: '0.5rem',
          }}
        >
          <span
            style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: '#64748b',
            }}
          >
            Workflow Modules
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
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 0.95rem',
                borderRadius: '10px',
                border: isActive
                  ? '1px solid rgba(56, 189, 248, 0.4)'
                  : '1px solid transparent',
                background: isActive
                  ? 'linear-gradient(90deg, rgba(56, 189, 248, 0.15), rgba(56, 189, 248, 0.05))'
                  : 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.88rem',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.18s ease-in-out',
                boxShadow: isActive ? '0 2px 10px rgba(56, 189, 248, 0.15)' : 'none',
              }}
              onMouseOver={(e) => {
                if (!isActive) {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                  btn.style.color = '#e2e8f0';
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Icon size={18} color={isActive ? '#38bdf8' : '#64748b'} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight size={15} color="#38bdf8" />}
            </button>
          );
        })}
      </div>

      {/* Footer / Role Context */}
      <div
        style={{
          padding: '1rem',
          borderRadius: '10px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.75rem',
          color: '#64748b',
        }}
      >
        <div style={{ fontWeight: 600, color: '#94a3b8', marginBottom: '2px' }}>
          Session Authorization
        </div>
        <div>
          Access Level: <span style={{ color: '#38bdf8', fontWeight: 600 }}>{role || 'PUBLIC'}</span>
        </div>
        <div style={{ fontSize: '0.7rem', marginTop: '4px', opacity: 0.8 }}>
          Governed under Digital India Land Records Modernization Programme (DILRMP)
        </div>
      </div>
    </aside>
  );
};
