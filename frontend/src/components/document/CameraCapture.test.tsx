// @vitest-environment jsdom
import React from 'react';
import { describe,it,expect,vi,beforeEach,afterEach } from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {CameraCapture} from './CameraCapture';

let stop: ReturnType<typeof vi.fn>;
let getUserMedia: ReturnType<typeof vi.fn>;
beforeEach(()=>{
  stop=vi.fn();getUserMedia=vi.fn().mockResolvedValue({getTracks:()=>[{stop}]});
  Object.defineProperty(window,'isSecureContext',{value:true,configurable:true});
  Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia},configurable:true});
  URL.createObjectURL=vi.fn(()=> 'blob:photo');URL.revokeObjectURL=vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype,'getContext').mockReturnValue({drawImage:vi.fn()} as any);
  vi.spyOn(HTMLCanvasElement.prototype,'toBlob').mockImplementation(callback=>callback(new Blob(['photo'],{type:'image/jpeg'})));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
describe('camera lifecycle',()=>{
  it('requests rear video only and stops on unmount',async()=>{
    const view=render(<CameraCapture onUse={vi.fn()} onClose={vi.fn()}/>);
    await waitFor(()=>expect(getUserMedia).toHaveBeenCalled());
    expect(getUserMedia.mock.calls[0][0]).toMatchObject({audio:false,video:{facingMode:{ideal:'environment'}}});
    view.unmount();expect(stop).toHaveBeenCalled();
  });
  it.each([['NotAllowedError','Camera permission was denied'],['NotFoundError','No camera was found']])('handles %s',async(name,message)=>{
    getUserMedia.mockRejectedValue({name});render(<CameraCapture onUse={vi.fn()} onClose={vi.fn()}/>);
    expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining(message));
  });
  it('captures locally, retakes, then supplies a JPEG File only on Use Photo',async()=>{
    const onUse=vi.fn();render(<CameraCapture onUse={onUse} onClose={vi.fn()}/>);
    await waitFor(()=>expect(getUserMedia).toHaveBeenCalled());
    const ready=()=>{
      const video=screen.getByLabelText('Live camera preview');
      Object.defineProperty(video,'videoWidth',{value:1600,configurable:true});Object.defineProperty(video,'videoHeight',{value:1000,configurable:true});
      fireEvent.loadedData(video);fireEvent.click(screen.getByText('Capture photo'));
    };
    ready();await screen.findByAltText('Captured document for review');expect(onUse).not.toHaveBeenCalled();expect(stop).toHaveBeenCalled();
    fireEvent.click(screen.getByText('Retake'));await waitFor(()=>expect(getUserMedia).toHaveBeenCalledTimes(2));
    ready();await screen.findByText('Use Photo');fireEvent.click(screen.getByText('Use Photo'));
    expect(onUse.mock.calls[0][0]).toBeInstanceOf(File);expect(onUse.mock.calls[0][0].type).toBe('image/jpeg');
  });
  it('stops a permission request that resolves after exit',async()=>{
    let resolve!: (value:any)=>void;getUserMedia.mockReturnValue(new Promise(r=>{resolve=r;}));
    const view=render(<CameraCapture onUse={vi.fn()} onClose={vi.fn()}/>);view.unmount();resolve({getTracks:()=>[{stop}]});
    await waitFor(()=>expect(stop).toHaveBeenCalled());
  });
  it('offers upload fallback outside secure contexts',()=>{
    Object.defineProperty(window,'isSecureContext',{value:false,configurable:true});
    render(<CameraCapture onUse={vi.fn()} onClose={vi.fn()}/>);expect(screen.getByRole('alert').textContent).toContain('HTTPS or localhost');expect(getUserMedia).not.toHaveBeenCalled();
  });
});
