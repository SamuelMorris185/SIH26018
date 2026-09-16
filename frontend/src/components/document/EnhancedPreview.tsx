import React, {useEffect,useState} from 'react';
import {documentsApi} from '../../api/documents';

export function EnhancedPreview({documentId,pages}:{documentId:string;pages:number[]}) {
  const [page,setPage]=useState(pages[0] || 1);
  const [open,setOpen]=useState(false);
  const [url,setUrl]=useState('');
  const [error,setError]=useState('');
  useEffect(()=>{
    if(!open)return;
    let cancelled=false,objectUrl='';setUrl('');setError('');
    documentsApi.fetchAnalysisPreview(documentId,page).then(blob=>{
      if(cancelled)return;objectUrl=URL.createObjectURL(blob);setUrl(objectUrl);
    }).catch(()=>{if(!cancelled)setError('Enhanced preview is unavailable. The original remains available in the Original Document tab.');});
    return()=>{cancelled=true;if(objectUrl)URL.revokeObjectURL(objectUrl);};
  },[documentId,page,open]);
  if(!pages.length)return null;
  return <section className="scanner-panel"><div className="scanner-heading"><h4>Original vs. OCR corrected image</h4><button className="scanner-button" onClick={()=>setOpen(v=>!v)}>{open?'Hide corrected image':'View OCR corrected image'}</button></div>
    <p className="scanner-help">The original is preserved in the Original Document tab. This preview reproduces geometric correction and grayscale preparation; threshold variants are not stored.</p>
    {open && <><label>Page <select aria-label="Enhanced preview page" value={page} onChange={e=>setPage(Number(e.target.value))}>{pages.map(n=><option key={n} value={n}>{n}</option>)}</select></label>
      {error?<p role="alert">{error}</p>:url?<img className="analysis-preview" src={url} alt={`OCR corrected document, page ${page}`}/>:<p role="status">Preparing corrected preview…</p>}</>}
  </section>;
}
