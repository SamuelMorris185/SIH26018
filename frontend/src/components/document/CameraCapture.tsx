import React, { useEffect, useRef, useState } from 'react';
import { Camera, RefreshCw, X, AlertTriangle, Check } from 'lucide-react';
import './document-analysis.css';

export function cameraFeedback(data: ImageData): string[] {
  const { width, height } = data;
  let sum = 0, gradients = 0, white = 0;
  const gray = (i: number) => .299*data.data[i]+.587*data.data[i+1]+.114*data.data[i+2];
  for (let y=1;y<height-1;y++) for (let x=1;x<width-1;x++) {
    const i=(y*width+x)*4, value=gray(i);
    sum+=value; white+=Number(value>250);
    gradients+=Math.abs(value-gray(i-4))+Math.abs(value-gray(i-width*4));
  }
  const pixels=Math.max(1,(width-2)*(height-2));
  const issues: string[]=[];
  if(sum/pixels<65) issues.push('Too dark — increase even lighting.');
  if(gradients/pixels<4) issues.push('Low detail — move closer or hold the camera steady.');
  if(white/pixels>.85) issues.push('Very bright frame — check for reflections or blank paper.');
  return issues;
}

const messages: Record<string,string> = {
  NotAllowedError: 'Camera permission was denied. Allow camera access in your browser, or upload a document.',
  NotFoundError: 'No camera was found. Connect a camera or upload a document.',
  NotReadableError: 'The camera is busy or unavailable. Close other camera applications and retry.',
};

export function CameraCapture({ onUse, onClose }: { onUse: (file: File) => void; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  const [facing,setFacing]=useState<'environment'|'user'>('environment');
  const [error,setError]=useState('');
  const [ready,setReady]=useState(false);
  const [photo,setPhoto]=useState<{file: File;url: string}|null>(null);
  const [issues,setIssues]=useState<string[]>([]);
  const [restart,setRestart]=useState(0);
  const stop=()=> { stream.current?.getTracks().forEach(track=>track.stop()); stream.current=null; };
  useEffect(()=> {
    const id=++generation.current;
    setReady(false); setError('');
    if(photo) return;
    if(!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError('Camera access requires HTTPS or localhost and a supported browser. You can still upload a document.');
      return;
    }
    navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:facing},width:{ideal:2560},height:{ideal:1920}}})
      .then(media=> {
        if(id!==generation.current) { media.getTracks().forEach(t=>t.stop()); return; }
        stream.current=media;
        if(video.current) video.current.srcObject=media;
      }).catch(err=> { if(id===generation.current) setError(messages[err.name] || 'Could not start the camera. Retry or upload a document.'); });
    return ()=> { generation.current++; stop(); };
  },[facing,photo,restart]);
  useEffect(()=>()=> { if(photo) URL.revokeObjectURL(photo.url); },[photo]);
  useEffect(()=> {
    if(!ready || photo) return;
    const timer=window.setInterval(()=> {
      const v=video.current; if(!v?.videoWidth) return;
      const canvas=document.createElement('canvas');canvas.width=320;canvas.height=Math.round(320*v.videoHeight/v.videoWidth);
      const ctx=canvas.getContext('2d');if(!ctx) return;
      ctx.drawImage(v,0,0,canvas.width,canvas.height);
      setIssues(cameraFeedback(ctx.getImageData(0,0,canvas.width,canvas.height)));
    },1200);
    return ()=>window.clearInterval(timer);
  },[ready,photo]);
  const capture=()=> {
    const v=video.current; if(!v?.videoWidth) return;
    const canvas=document.createElement('canvas');
    const scale=Math.min(1,3200/Math.max(v.videoWidth,v.videoHeight));
    canvas.width=Math.round(v.videoWidth*scale); canvas.height=Math.round(v.videoHeight*scale);
    const ctx=canvas.getContext('2d');if(!ctx) { setError('Photo capture is unavailable. Please upload a file.'); return; }
    ctx.drawImage(v,0,0,canvas.width,canvas.height);
    const id=generation.current;
    canvas.toBlob(blob=> {
      if(!blob || id!==generation.current) return;
      const file=new File([blob],`land-record-${new Date().toISOString().replace(/[:.]/g,'-')}.jpg`,{type:'image/jpeg'});
      setPhoto({file,url:URL.createObjectURL(blob)});stop();
    },'image/jpeg',.94);
  };
  return <section className="scanner-panel" aria-label="Document camera">
    <div className="scanner-heading"><div><p className="technical-kicker">// DOCUMENT SCANNER</p><h3>Capture a land record</h3></div><button type="button" className="scanner-button" aria-label="Close camera" onClick={()=>{generation.current++;stop();onClose();}}><X size={18}/></button></div>
    {error ? <div role="alert" className="analysis-warning"><AlertTriangle size={18}/><span>{error}</span><button type="button" className="scanner-button" onClick={()=>setRestart(x=>x+1)}>Retry camera</button></div> : <>
      <div className="camera-stage">
        {photo ? <img src={photo.url} alt="Captured document for review"/> : <><video ref={video} autoPlay muted playsInline onLoadedData={()=>setReady(true)} aria-label="Live camera preview"/><div className="camera-guide" aria-hidden="true"/></>}
      </div>
      <p className="scanner-help">{photo ? 'Check that every field is readable before using this photo.' : 'Place the full document inside the frame. Keep all four edges visible and avoid direct reflections.'}</p>
      <div aria-live="polite">{issues.length>0 ? issues.map(issue=><p className="scanner-advice" key={issue}><AlertTriangle size={15}/>{issue}</p>) : <p className="scanner-help">{ready || photo ? 'Basic lighting/detail check complete. Full quality analysis runs during processing.' : 'Waiting for camera preview…'}</p>}</div>
      <p className="scanner-help">Live checks are approximate; they do not verify document edges, perspective, or authenticity.</p>
      <div className="scanner-actions">{photo ? <>
        <button type="button" className="scanner-button" onClick={()=>{setPhoto(null);setIssues([]);}}>Retake</button>
        <button type="button" className="scanner-button primary" onClick={()=>{stop();onUse(photo.file);onClose();}}><Check size={16}/>Use Photo</button>
      </> : <>
        <button type="button" className="scanner-button" onClick={()=>{stop();setFacing(f=>f==='environment'?'user':'environment');}}><RefreshCw size={16}/>Switch camera</button>
        <button type="button" className="scanner-button primary" disabled={!ready} onClick={capture}><Camera size={16}/>{issues.length ? 'Capture Anyway' : 'Capture photo'}</button>
      </>}</div>
    </>}
  </section>;
}
