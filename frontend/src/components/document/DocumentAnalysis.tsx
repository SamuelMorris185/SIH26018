import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { DocumentAnalysisResult } from '../../types';
import './document-analysis.css';

export function DocumentAnalysis({ analysis }: {analysis?: DocumentAnalysisResult | null}) {
  if(!analysis) return <p className="scanner-help">Document quality and authenticity analysis are unavailable for this older extraction.</p>;
  return <section className="document-analysis" aria-label="Document analysis results">
    <div><p className="technical-kicker">// DOCUMENT INTELLIGENCE</p><h3>Quality, OCR & authenticity risk</h3></div>
    <p className="scanner-help">Languages: {analysis.languages.join(', ')} · {analysis.passes.length} OCR pass(es) · {analysis.elapsed_seconds}s</p>
    {analysis.missing_languages.length>0 && <p className="scanner-help">Optional language data unavailable: {analysis.missing_languages.join(', ')}</p>}
    {analysis.requires_manual_review && <div className="analysis-warning" role="status"><AlertTriangle size={20}/><div><strong>Manual verification required</strong>{analysis.review_reasons.map(reason=><p key={reason}>{reason}</p>)}</div></div>}
    {analysis.pages.map(page=><div key={page.page} className="analysis-page">
      <h4>Page {page.page} · {page.input_type.replace(/_/g,' ')}</h4>
      {page.quality ? <>
        <div className="analysis-metrics">{([
          ['Quality',page.quality.quality_score],['Sharpness',page.quality.blur_score],['Lighting',page.quality.brightness_score],
          ['Contrast',page.quality.contrast_score],['Resolution',page.quality.resolution_score],['Possible glare %',page.quality.glare_score],
        ] as [string,number][]).map(([label,value])=><div className="analysis-metric" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
        <p className="scanner-help">{page.quality.recommended_action.replace(/_/g,' ')} · Detected skew: {page.quality.skew_angle}°</p>
        <ul>{page.quality.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>
      </> : <p className="scanner-help">Digital PDF text read directly. Pixel quality was not assessed.</p>}
      <p className="scanner-help">Corrections: {page.preprocessing.operations.join(', ') || 'None needed'} · Orientation: {page.preprocessing.orientation_degrees ?? 0}°</p>
      <div className="scanner-heading"><h4><ShieldCheck size={16}/> Authenticity risk: {page.authenticity.assessed===false ? 'NOT ASSESSED' : page.authenticity.risk_level}</h4><span className="evidence-note">{page.authenticity.assessed===false ? '' : `${page.authenticity.risk_score}/100 · heuristic score`}</span></div>
      {page.authenticity.signals.length ? <ul>{page.authenticity.signals.map(signal=><li key={signal.code}><strong>{signal.code.replace(/_/g,' ')}</strong>: {signal.explanation}<details><summary>Evidence</summary><pre>{JSON.stringify(signal.evidence,null,2)}</pre></details></li>)}</ul> : <p className="scanner-help">No risk signals reported. This does not establish authenticity.</p>}
      <p className="scanner-help">{page.authenticity.disclaimer}</p>
      <details><summary className="scanner-help">Analysis limitations</summary><ul>{page.authenticity.limitations.map(item=><li key={item}>{item}</li>)}</ul></details>
    </div>)}
  </section>;
}
