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
  Sparkles,
} from 'lucide-react';
import { documentsApi } from '../api/documents';
import { useNavigation } from '../context/NavigationContext';
import { useToast } from '../context/ToastContext';
import { DigitizationPipelineResult } from '../types';
import { ConfidenceBadge } from '../components/confidence/ConfidenceBadge';
import { StatusBadge } from '../components/ui/StatusBadge';
import { CameraCapture } from '../components/document/CameraCapture';
import { DocumentAnalysis } from '../components/document/DocumentAnalysis';

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
  const [cameraOpen, setCameraOpen] = useState(false);

  const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];
  const maxSizeBytes = 10 * 1024 * 1024; // 10MB

  const steps = [
    'Secure Document Ingestion & Verification',
    'Image Preprocessing (Grayscale, Contrast, Rescale)',
    'Configured Multi-Lingual OCR Extraction Engine',
    'Deterministic Revenue Field Normalization',
    'Statutory Rule-Based Validation Check',
    'Parcel Identity Cross-Examination & Discrepancy Match',
  ];

  const validateAndSelectFile = (file: File) => {
    if (isProcessing) return;
    setSelectedFile(null);
    setError(null);
    setResult(null);

    if (file.size === 0) {
      setError('Selected file is empty (0 bytes). Please select a valid document.');
      return;
    }
    if (file.size > maxSizeBytes) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds 10 MB upload limit.`);
      return;
    }

    const name = file.name.toLowerCase();
    const hasValidExt = allowedExtensions.some((ext) => name.endsWith(ext));
    if (!hasValidExt) {
      setError(`Unsupported file format. Supported formats: PDF, PNG, JPG, JPEG, TIFF.`);
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

    try {
      const pipelineResult = await documentsApi.uploadAndProcess(selectedFile, docType);
      setCurrentStep(6);
      setResult(pipelineResult);
      success('Document processed. Check the analysis and review requirements below.');
    } catch (err: any) {
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
        <h2 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
          Document Ingestion &amp; Processing Gateway
        </h2>
        <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '3px' }}>
          Upload scanned revenue records or digital land titles for automated multi-lingual OCR parsing and cross-validation
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
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '12px',
            color: '#f87171',
          }}
        >
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '0.88rem' }}>{error}</span>
        </div>
      )}

      {!result && !isProcessing && <div className="scanner-actions">
        <button type="button" className="scanner-button" onClick={()=>{setCameraOpen(false);fileInputRef.current?.click();}}>Upload Document</button>
        <button type="button" className="scanner-button primary" onClick={()=>setCameraOpen(true)}>Take Photo</button>
        {selectedFile && <button type="button" className="scanner-button" onClick={()=>{setSelectedFile(null);if(fileInputRef.current)fileInputRef.current.value='';}}>Remove selected file</button>}
      </div>}
      {cameraOpen && <CameraCapture onUse={validateAndSelectFile} onClose={()=>setCameraOpen(false)}/>}
      {result && <DocumentAnalysis analysis={result.extraction.analysis}/>}
      {/* Upload Zone & Config Card */}
      {!result && (
        <div className="bento-card" style={{ padding: '2rem' }}>
          {/* Document Type Selector */}
          <div style={{ marginBottom: '1.75rem' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.8rem',
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
                maxWidth: '380px',
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
              border: `2px dashed ${isDragging ? '#38bdf8' : selectedFile ? '#10b981' : 'rgba(51, 65, 85, 0.6)'}`,
              borderRadius: '18px',
              padding: '3.5rem 2rem',
              textAlign: 'center',
              backgroundColor: isDragging
                ? 'rgba(56, 189, 248, 0.08)'
                : selectedFile
                ? 'rgba(16, 185, 129, 0.04)'
                : 'rgba(15, 23, 42, 0.5)',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease-in-out',
              boxShadow: isDragging ? '0 0 25px rgba(56, 189, 248, 0.2)' : 'none',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
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
                border: selectedFile ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(56, 189, 248, 0.3)',
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
                <div style={{ fontWeight: 700, fontSize: '1.15rem', color: '#f8fafc' }}>
                  {selectedFile.name}
                </div>
                <div className="font-mono" style={{ fontSize: '0.8rem', color: '#34d399', marginTop: '4px' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB • Ready for Automated AI Processing
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '8px' }}>
                  Click or drop a different file to replace
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem', color: '#f8fafc' }}>
                  Drag &amp; Drop Land Document Here
                </div>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '6px' }}>
                  or click to browse local device files
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    marginTop: '1.25rem',
                  }}
                >
                  {['PDF', 'PNG', 'JPEG', 'TIFF'].map((ext) => (
                    <span
                      key={ext}
                      className="font-mono"
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        background: 'rgba(255, 255, 255, 0.04)',
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
                <div className="font-mono" style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '8px' }}>
                  Max size: 10 MB per document
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={executePipeline}
              disabled={!selectedFile || isProcessing}
              className="btn btn-primary"
              style={{
                padding: '0.75rem 1.75rem',
                fontSize: '0.92rem',
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
        <div className="bento-card" style={{ padding: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1.5rem' }}>
            <Loader2 size={24} color="#38bdf8" className="animate-spin" />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>
              Processing document — waiting for server results
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {steps.map((step, idx) => {
              const isDone = false;
              const isCurrent = false;

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '0.75rem 1rem',
                    borderRadius: '10px',
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
                      color: isDone ? '#f8fafc' : isCurrent ? '#38bdf8' : '#64748b',
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
          className="bento-card"
          style={{
            padding: '2rem',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            backgroundColor: 'rgba(16, 185, 129, 0.05)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
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
                Processing completed. Validation and review outcomes are shown below.
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
            <div style={{ padding: '1rem', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div className="font-mono" style={{ fontSize: '0.72rem', color: '#94a3b8' }}>OVERALL CONFIDENCE</div>
              <div style={{ marginTop: '6px' }}>
                <ConfidenceBadge score={result.extraction.confidence_score} size="md" />
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div className="font-mono" style={{ fontSize: '0.72rem', color: '#94a3b8' }}>VALIDATION STATUS</div>
              <div style={{ marginTop: '6px' }}>
                <StatusBadge status={newlyCreatedRecord?.status || 'VALIDATED'} size="md" />
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div className="font-mono" style={{ fontSize: '0.72rem', color: '#94a3b8' }}>OCR ENGINE USED</div>
              <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8', marginTop: '6px' }}>
                {result.extraction.provider}
              </div>
            </div>

            <div style={{ padding: '1rem', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div className="font-mono" style={{ fontSize: '0.72rem', color: '#94a3b8' }}>DISCREPANCIES DETECTED</div>
              <div
                className="font-mono"
                style={{
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  color: result.discrepancies?.total_discrepancies ? '#fb7185' : '#34d399',
                  marginTop: '6px',
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
              className="btn btn-secondary"
            >
              Upload Another
            </button>

            {newlyCreatedRecord && (
              <button
                onClick={() => navigate('record-detail', { recordId: newlyCreatedRecord.id })}
                className="btn btn-primary"
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
