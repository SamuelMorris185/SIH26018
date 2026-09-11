import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Cpu,
  ShieldCheck,
  Loader2,
} from 'lucide-react';
import { documentsApi } from '../api/documents';
import { useNavigation } from '../context/NavigationContext';
import { useToast } from '../context/ToastContext';
import { DigitizationPipelineResult } from '../types';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';
import { StatusBadge } from '../components/ui/StatusBadge';

export const DocumentUpload: React.FC = () => {
  const { navigate } = useNavigation();
  const { success, error: toastError } = useToast();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>('JAMABANDI');
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [result, setResult] = useState<DigitizationPipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp'];
  const maxSizeBytes = 10 * 1024 * 1024; // 10MB

  const steps = [
    'Secure Document Upload & Verification',
    'Image Preprocessing (Grayscale, Contrast, Rescale)',
    'Real Tesseract OCR Extraction Engine',
    'Deterministic Revenue Field Normalization',
    'Statutory Rule-Based Validation Check',
    'Parcel Identity Cross-Examination & Discrepancy Match',
  ];

  const validateAndSelectFile = (file: File) => {
    setError(null);
    setResult(null);

    if (file.size === 0) {
      setError('Selected file is empty (0 bytes). Please select a valid document.');
      return;
    }
    if (file.size > maxSizeBytes) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds statutory 10 MB limit.`);
      return;
    }

    const name = file.name.toLowerCase();
    const hasValidExt = allowedExtensions.some((ext) => name.endsWith(ext));
    if (!hasValidExt) {
      setError(`Unsupported file format. Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP.`);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const executePipeline = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);
    setResult(null);
    setCurrentStep(0);

    // Simulate animated step progression while backend processes
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < 5 ? prev + 1 : prev));
    }, 600);

    try {
      const pipelineResult = await documentsApi.uploadAndProcess(selectedFile, docType);
      clearInterval(stepInterval);
      setCurrentStep(6);
      setResult(pipelineResult);
      success('Document digitized and validated successfully!');
    } catch (err: any) {
      clearInterval(stepInterval);
      const msg = err?.message || 'Pipeline processing failed';
      setError(msg);
      toastError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const newlyCreatedRecord = result?.records && result.records.length > 0 ? result.records[0] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem', maxWidth: '960px', margin: '0 auto' }}>
      {/* Page Header */}
      <div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
          Document Ingestion & Processing Gateway
        </h2>
        <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
          Upload scanned revenue records or digital land titles for automated Tesseract OCR parsing and validation
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '1rem',
            backgroundColor: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            borderRadius: '12px',
            color: '#fecdd3',
          }}
        >
          <AlertCircle size={20} color="#f43f5e" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '0.88rem' }}>{error}</span>
        </div>
      )}

      {/* Upload Zone & Config Card */}
      {!result && (
        <div className="glass-panel" style={{ padding: '2rem' }}>
          {/* Document Type Selector */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: '#cbd5e1',
                marginBottom: '0.5rem',
              }}
            >
              Revenue Document Classification
            </label>
            <select
              value={docType}
              disabled={isProcessing}
              onChange={(e) => setDocType(e.target.value)}
              style={{
                width: '100%',
                maxWidth: '360px',
                padding: '0.65rem 0.85rem',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '8px',
                color: '#f8fafc',
                fontSize: '0.88rem',
                outline: 'none',
              }}
            >
              <option value="JAMABANDI">Jamabandi (Record of Rights / RoR)</option>
              <option value="KHASRA_KHATONI">Khasra-Khatoni Registry</option>
              <option value="SALE_DEED">Registered Sale Deed</option>
              <option value="MUTATION_REGISTER">Namantaran (Mutation Register)</option>
            </select>
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => !isProcessing && fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? '#38bdf8' : selectedFile ? '#10b981' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: '16px',
              padding: '3rem 2rem',
              textAlign: 'center',
              backgroundColor: isDragging
                ? 'rgba(56, 189, 248, 0.08)'
                : selectedFile
                ? 'rgba(16, 185, 129, 0.04)'
                : 'rgba(15, 23, 42, 0.4)',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  validateAndSelectFile(e.target.files[0]);
                }
              }}
              style={{ display: 'none' }}
            />

            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '16px',
                backgroundColor: selectedFile ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.25rem auto',
              }}
            >
              {selectedFile ? (
                <FileText size={32} color="#10b981" />
              ) : (
                <UploadCloud size={32} color="#38bdf8" />
              )}
            </div>

            {selectedFile ? (
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#f8fafc' }}>
                  {selectedFile.name}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#34d399', marginTop: '4px' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB • Ready for Automated Processing
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '8px' }}>
                  Click or drop a different file to replace
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#f8fafc' }}>
                  Drag & Drop Land Document Here
                </div>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '6px' }}>
                  or click to browse your local device
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    marginTop: '1rem',
                  }}
                >
                  {['PDF', 'PNG', 'JPEG', 'TIFF', 'BMP'].map((ext) => (
                    <span
                      key={ext}
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        color: '#94a3b8',
                      }}
                    >
                      {ext}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '8px' }}>
                  Maximum file size: 10 MB per document
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={executePipeline}
              disabled={!selectedFile || isProcessing}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '0.85rem 1.75rem',
                backgroundColor: !selectedFile || isProcessing ? '#1e293b' : '#0284c7',
                color: !selectedFile || isProcessing ? '#64748b' : '#ffffff',
                border: 'none',
                borderRadius: '10px',
                fontSize: '0.92rem',
                fontWeight: 700,
                cursor: !selectedFile || isProcessing ? 'not-allowed' : 'pointer',
                boxShadow: !selectedFile || isProcessing ? 'none' : '0 4px 15px rgba(2, 132, 199, 0.4)',
                transition: 'all 0.2s',
              }}
            >
              {isProcessing ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Cpu size={18} />
                  <span>Start AI Digitization Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Processing Animation Tracker */}
      {isProcessing && (
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1.5rem' }}>
            <Loader2 size={24} color="#38bdf8" className="animate-spin" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
              Executing Real Intelligent Land Pipeline
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {steps.map((step, idx) => {
              const isDone = currentStep > idx;
              const isCurrent = currentStep === idx;

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    backgroundColor: isCurrent
                      ? 'rgba(56, 189, 248, 0.08)'
                      : isDone
                      ? 'rgba(16, 185, 129, 0.05)'
                      : 'transparent',
                    border: isCurrent
                      ? '1px solid rgba(56, 189, 248, 0.3)'
                      : '1px solid transparent',
                  }}
                >
                  <div style={{ width: '20px', display: 'flex', justifyContent: 'center' }}>
                    {isDone ? (
                      <CheckCircle2 size={18} color="#10b981" />
                    ) : isCurrent ? (
                      <Loader2 size={16} color="#38bdf8" className="animate-spin" />
                    ) : (
                      <div
                        style={{
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          backgroundColor: '#334155',
                        }}
                      />
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: '0.88rem',
                      fontWeight: isCurrent ? 700 : 500,
                      color: isDone ? '#e2e8f0' : isCurrent ? '#38bdf8' : '#64748b',
                    }}
                  >
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Success Result View */}
      {result && (
        <div
          className="glass-panel"
          style={{
            padding: '2rem',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            backgroundColor: 'rgba(6, 78, 59, 0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ShieldCheck size={28} color="#10b981" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc' }}>
                Digitization Pipeline Completed
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#34d399', marginTop: '2px' }}>
                Document successfully ingested, parsed with Tesseract OCR, normalized, and validated
              </p>
            </div>
          </div>

          {/* Metrics summary */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem',
            }}
          >
            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Overall Confidence</div>
              <div style={{ marginTop: '4px' }}>
                <ConfidenceBadge score={result.extraction.confidence_score} size="md" />
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Validation Status</div>
              <div style={{ marginTop: '4px' }}>
                <StatusBadge status={newlyCreatedRecord?.status || 'VALIDATED'} size="md" />
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>OCR Engine Used</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                {result.extraction.provider}
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: '10px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Discrepancies Detected</div>
              <div
                style={{
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  color: result.discrepancies?.total_discrepancies ? '#fb7185' : '#34d399',
                  marginTop: '4px',
                }}
              >
                {result.discrepancies?.total_discrepancies ?? 0} Conflicts
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              onClick={() => {
                setResult(null);
                setSelectedFile(null);
              }}
              style={{
                padding: '0.7rem 1.25rem',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '8px',
                color: '#e2e8f0',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Upload Another
            </button>

            {newlyCreatedRecord && (
              <button
                onClick={() => navigate('record-detail', { recordId: newlyCreatedRecord.id })}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '0.7rem 1.4rem',
                  backgroundColor: '#0284c7',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(2, 132, 199, 0.4)',
                }}
              >
                <span>View Full Record Details</span>
                <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
