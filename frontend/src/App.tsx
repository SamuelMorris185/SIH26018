import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NavigationProvider, useNavigation } from './context/NavigationContext';
import { ToastProvider } from './context/ToastContext';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { RecordsList } from './pages/RecordsList';
import { RecordDetail } from './pages/RecordDetail';
import { DocumentUpload } from './pages/DocumentUpload';
import { DiscrepanciesList } from './pages/DiscrepanciesList';
import { ReviewWorkspace } from './pages/ReviewWorkspace';
import { AuditLogsView } from './pages/AuditLogsView';
import { SystemStatus } from './pages/SystemStatus';
import { CadastralMap } from './pages/CadastralMap';

const MainLayout: React.FC = () => {

  const { isAuthenticated, isLoading } = useAuth();
  const { currentView } = useNavigation();
  const sectionLabels: Record<string, string> = {
    dashboard: '// 01 — DASHBOARD',
    upload: '// 02 — DOCUMENT DIGITIZATION',
    records: '// 03 — LAND RECORDS',
    discrepancies: '// 04 — VALIDATION',
    review: '// 05 — REVIEW',
    'cadastral-map': '// 06 — CADASTRAL GIS',
    audit: '// 07 — AUDIT TRAIL',
    'record-detail': '// RECORD DOSSIER INTELLIGENCE',
    system: '// 08 — SYSTEM DIAGNOSTICS',
  };

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0a0d14',
          color: '#38bdf8',
          gap: '1rem',
        }}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(56, 189, 248, 0.2)',
            borderTopColor: '#38bdf8',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8' }}>
          Loading Revenue Authentication Gateway...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'records':
        return <RecordsList />;
      case 'record-detail':
        return <RecordDetail />;
      case 'upload':
        return <DocumentUpload />;
      case 'discrepancies':
        return <DiscrepanciesList />;
      case 'review':
        return <ReviewWorkspace />;
      case 'audit':
        return <AuditLogsView />;
      case 'system':
        return <SystemStatus />;
      case 'cadastral-map':
        return <CadastralMap />;
      default:
        return <Dashboard />;

    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        backgroundColor: 'var(--bg-primary)',
      }}
    >
      <Header />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main
          className="animate-page-enter"
          style={{
            flex: 1,
            padding: '2rem',
            overflowY: 'auto',
            maxHeight: 'calc(100vh - 70px)',
          }}
        >
          <div className="technical-kicker" aria-hidden="true">{sectionLabels[currentView]}</div>
          {renderView()}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <NavigationProvider>
          <MainLayout />
        </NavigationProvider>
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
