import React, { useState } from 'react';
import { Shield, Lock, Mail, AlertCircle, ArrowRight, UserCheck, Eye, EyeOff, CheckCircle2, Layers, Cpu, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export const Login: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuth();
  const { success } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim()) {
      setLocalError('Please enter your official email address');
      return;
    }
    if (!password) {
      setLocalError('Please enter your password');
      return;
    }

    try {
      await login(email.trim(), password);
      success('Authentication verified. Welcome to Bhu-Abhilekh AI.');
    } catch {
      // Error handled by AuthContext
    }
  };

  const setDemoCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setLocalError(null);
    clearError();
  };

  const activeError = localError || error;

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: '#080c14',
        backgroundImage: `
          radial-gradient(ellipse at 15% 20%, rgba(14, 165, 233, 0.12) 0%, transparent 50%),
          radial-gradient(ellipse at 85% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
          linear-gradient(rgba(56, 189, 248, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(56, 189, 248, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: '100% 100%, 100% 100%, 40px 40px, 40px 40px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1100px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
          gap: '3rem',
          alignItems: 'center',
          zIndex: 10,
        }}
      >
        {/* LEFT HERO AREA — Inspired by Samuel Morris Portfolio Hero */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Status badge pill */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.35rem 0.85rem',
              borderRadius: '9999px',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontSize: '0.78rem',
              fontWeight: 600,
              width: 'fit-content',
            }}
          >
            <span className="status-dot status-dot-green" />
            <span className="font-mono" style={{ letterSpacing: '0.04em' }}>// DILRMP GOVERNANCE STANDARDS COMPLIANT</span>
          </div>

          <p className="technical-kicker">// 00 — AUTHENTICATION GATEWAY</p>

          <h1
            style={{
              fontSize: '2.75rem',
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 60%, #38bdf8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            SIH26018 Platform
          </h1>

          <h2
            style={{
              fontSize: '1.25rem',
              fontWeight: 600,
              color: '#38bdf8',
              lineHeight: 1.4,
            }}
          >
            Intelligent Land Record Digitization &amp; Validation System
          </h2>

          <p
            style={{
              fontSize: '0.92rem',
              color: '#94a3b8',
              lineHeight: 1.65,
              maxWidth: '480px',
            }}
          >
            Automating multi-lingual OCR extraction, rule-based cross-validation, AI discrepancy detection, and Cadastral GIS parcel linkage for state revenue departments.
          </p>

          {/* Bento Tech Feature Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
            <span className="pill-filter active">
              <Cpu size={14} /> Multi-Lingual OCR AI
            </span>
            <span className="pill-filter active">
              <Layers size={14} /> Cross-Validation Engine
            </span>
            <span className="pill-filter active">
              <MapPin size={14} /> Cadastral GIS Linkage
            </span>
            <span className="pill-filter active">
              <CheckCircle2 size={14} /> Audit Ledger
            </span>
          </div>
        </div>

        {/* RIGHT SECURE LOGIN CARD */}
        <div
          className="glass-panel"
          style={{
            padding: '2.5rem',
            borderRadius: '24px',
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(56, 189, 248, 0.1)',
          }}
        >
          <div style={{ marginBottom: '1.75rem', textAlign: 'center' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                background: 'linear-gradient(135deg, #0ea5e9, #2563eb)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(14, 165, 233, 0.4)',
                marginBottom: '1rem',
              }}
            >
              <Shield size={26} color="#ffffff" />
            </div>
            <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#f8fafc' }}>
              Official Login
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
              Sign in with your revenue department credentials
            </p>
          </div>

          {activeError && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                padding: '0.75rem 1rem',
                borderRadius: '10px',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#f87171',
                fontSize: '0.82rem',
                marginBottom: '1.25rem',
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{activeError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#cbd5e1',
                  marginBottom: '0.4rem',
                }}
              >
                Official Email
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={18}
                  color="#64748b"
                  style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
                />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@revenue.gov.in"
                  style={{ paddingLeft: '2.5rem' }}
                  disabled={isLoading}
                />
              </div>
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#cbd5e1',
                  marginBottom: '0.4rem',
                }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={18}
                  color="#64748b"
                  style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }}
                />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{ paddingLeft: '2.5rem', paddingRight: '2.5rem' }}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: '2px',
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '0.92rem',
                marginTop: '0.5rem',
              }}
            >
              {isLoading ? (
                <>
                  <div
                    style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#fff',
                      borderRadius: '50%',
                    }}
                    className="animate-spin"
                  />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Governance Portal</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Quick-fill Demo Roles */}
          <div style={{ marginTop: '1.75rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <p className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              // DEMO ROLE QUICK-FILL
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
              <button
                type="button"
                className="pill-filter"
                onClick={() => setDemoCredentials('admin@sih26018.gov.in', 'Admin@123456')}
                style={{ justifyContent: 'center' }}
              >
                <UserCheck size={13} /> System Admin
              </button>
              <button
                type="button"
                className="pill-filter"
                onClick={() => setDemoCredentials('reviewer@sih26018.gov.in', 'Reviewer@123456')}
                style={{ justifyContent: 'center' }}
              >
                <UserCheck size={13} /> Land Reviewer
              </button>
              <button
                type="button"
                className="pill-filter"
                onClick={() => setDemoCredentials('operator@sih26018.gov.in', 'Operator@123456')}
                style={{ justifyContent: 'center' }}
              >
                <UserCheck size={13} /> Revenue Operator
              </button>
              <button
                type="button"
                className="pill-filter"
                onClick={() => setDemoCredentials('viewer@sih26018.gov.in', 'Viewer@123456')}
                style={{ justifyContent: 'center' }}
              >
                <UserCheck size={13} /> Citizen Viewer
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
