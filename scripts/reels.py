#!/usr/bin/env python3
"""Local source → transcript → agent-selected plan → HTML motion + paired video → MP4."""
import argparse, base64, functools, hashlib, http.server, json, math, os, re, shutil, subprocess, sys, threading
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def ffmpeg():
    if os.environ.get('REELS_FFMPEG'):
        return os.environ['REELS_FFMPEG']
    executable = shutil.which('ffmpeg')
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise ValueError('FFmpeg runtime missing. Run scripts/bootstrap.py first.')

def run(argv):
    p = subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise ValueError('Command failed: '+p.stderr[-3500:])
    return p.stdout

def probe(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'Missing media: {path}')
    executable = shutil.which('ffprobe')
    if executable:
        info = json.loads(run([executable, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]))
        vs = next((s for s in info['streams'] if s['codec_type'] == 'video'), {})
        duration = float(info.get('format', {}).get('duration', vs.get('duration', 0)))
        return {'duration': duration, 'width': vs.get('width'), 'height': vs.get('height'),
                'audio': any(s['codec_type'] == 'audio' for s in info['streams']), 'streams': info['streams']}
    # Portable fallback: bundled FFmpeg is sufficient; ffprobe is optional.
    p = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(path)], capture_output=True, text=True)
    text = p.stderr
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
    if not m:
        raise ValueError(f'Cannot determine duration of {path}; install ffprobe for this container.')
    dims = re.search(r'Video:.*?\b(\d{2,5})x(\d{2,5})\b', text)
    return {'duration': int(m[1])*3600+int(m[2])*60+float(m[3]),
            'width': int(dims[1]) if dims else None, 'height': int(dims[2]) if dims else None,
            'audio': bool(re.search(r'Stream .*Audio:', text)), 'streams': []}

def stamp(t):
    ms = round(t*1000)
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def write_srt(cues, path):
    Path(path).write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i,c in enumerate(cues))+'\n', encoding='utf-8')

def read_captions(path):
    path = Path(path)
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        data = data.get('cues', data.get('segments', [])) if isinstance(data, dict) else data
        return [{'start': float(c['start']), 'end': float(c['end']), 'text': c['text']} for c in data]
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    pattern = re.compile(r'(?m)^(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})[^\n]*\n')
    matches = list(pattern.finditer(text)); cues = []
    for i, match in enumerate(matches):
        a = match.groups()
        start = (int(a[0] or 0)*3600000+int(a[1])*60000+int(a[2])*1000+int(a[3]))/1000
        end = (int(a[4] or 0)*3600000+int(a[5])*60000+int(a[6])*1000+int(a[7]))/1000
        tail = text[match.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        # Remove cue IDs from the following block, preserve multi-line text.
        caption = tail.split('\n\n',1)[0].strip()
        caption = re.sub(r'<[^>]*>', '', caption)
        if caption: cues.append({'start': start, 'end': end, 'text': caption})
    return cues

def browser(runtime):
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(Path(runtime)/'browsers')
    from playwright.sync_api import sync_playwright
    return sync_playwright()

def frames(args):
    info=probe(args.source); args.output.mkdir(parents=True,exist_ok=True)
    vf=[]
    if args.crop:
        x,y,w,h=args.crop
        if min(x,y)<0 or min(w,h)<=0 or x+w>info['width'] or y+h>info['height']: raise ValueError('crop outside source')
        vf.append(f'crop={w}:{h}:{x}:{y}')
    vf.append('scale=960:-2')
    for i,t in enumerate(args.times):
        if not 0<=t<info['duration']: raise ValueError('Frame time outside source')
        run([ffmpeg(),'-v','error','-y','-ss',t,'-i',args.source,'-frames:v','1','-vf',','.join(vf),args.output/f'{i:02}-{t:.3f}.jpg'])
    print(f'Saved {len(args.times)} source frames; stills are for selection, not a replacement for live proof.')

def sync(args):
    import numpy as np
    for path in [args.master,args.secondary]:
        if not probe(path)['audio']: raise ValueError('Automatic sync needs shared audio on both sources; use an observed event for silent video.')
    envelopes=[]
    for path in [args.master,args.secondary]:
        p=subprocess.run([ffmpeg(),'-v','error','-i',str(path),'-vn','-t',str(args.window),'-ar','8000','-ac','1','-f','s16le','pipe:1'],capture_output=True,check=True)
        samples=np.frombuffer(p.stdout,dtype='<i2').astype(float)/32768
        samples=samples[:len(samples)//80*80].reshape(-1,80)
        e=np.sqrt(np.mean(samples*samples,axis=1)); e=(e-e.mean())/(e.std()+1e-9)
        if np.std(e)<.01: raise ValueError('Insufficient voice variation for reliable sync')
        envelopes.append(e)
    a,b=envelopes; n=1<<(len(a)+len(b)-1).bit_length()
    corr=np.fft.irfft(np.fft.rfft(a,n)*np.conj(np.fft.rfft(b,n)),n)
    lags=np.arange(-len(b)+1,len(a)); vals=np.concatenate((corr[-len(b)+1:],corr[:len(a)]))
    overlap=np.minimum(len(a),len(b)+lags)-np.maximum(0,lags)
    valid=(overlap>=min(1000,min(len(a),len(b))*.6))&(np.abs(lags)<=args.max_offset*100)
    if not valid.any(): raise ValueError('No sufficient audio overlap in search window')
    scores=np.where(valid,vals/np.maximum(overlap,1),-np.inf); k=int(np.argmax(scores)); lag=int(lags[k])
    aa=a[max(0,lag):min(len(a),len(b)+lag)]; bb=b[max(0,-lag):min(len(b),len(a)-lag)]
    score=float(np.corrcoef(aa,bb)[0,1]); offset=-lag/100
    far=valid & (np.abs(lags-lag)>100)
    if far.any() and np.max(scores[far])>scores[k]*.94:
        raise ValueError('Ambiguous repeated audio pattern; verify a common event manually instead of using this candidate.')
    result={'offset_seconds':offset,'convention':'secondary_time = master_time + offset_seconds','correlation':score,'status':'candidate; verify a common event at start and end', 'window_seconds':args.window}
    if not math.isfinite(score) or score<.55: raise ValueError('Low-confidence audio match; check shared events manually rather than apply an uncertain offset.')
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

def doctor(args):
    checks = {'python': sys.version.split()[0], 'ffmpeg': run([ffmpeg(), '-version']).splitlines()[0]}
    import importlib.metadata
    for pkg in ['playwright', 'imageio-ffmpeg']:
        checks[pkg] = importlib.metadata.version(pkg)
    try: checks['faster-whisper'] = importlib.metadata.version('faster-whisper')
    except importlib.metadata.PackageNotFoundError: checks['faster-whisper'] = 'not installed; captions required'
    checks['font'] = (args.runtime/'NotoSansTC.ttf').is_file()
    if not checks['font']: raise ValueError('CJK font missing; run bootstrap.')
    with browser(args.runtime) as p:
        b = p.chromium.launch(); page = b.new_page(); page.set_content('<p>runtime</p>')
        assert page.locator('p').inner_text() == 'runtime'; b.close()
    checks['browser'] = 'launch and HTML render OK'
    print(json.dumps(checks, ensure_ascii=False, indent=2))

def prepare(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve(); info = probe(source)
    if not info['audio']: raise ValueError('Source has no voice track; supply an audio or talking source.')
    if args.transcript:
        cues = read_captions(args.transcript)
        mode = 'provided transcript; accuracy not verified'
    else:
        try: from faster_whisper import WhisperModel
        except ImportError: raise ValueError('No transcript supplied and ASR is unavailable; rerun bootstrap without --no-asr.')
        wav = out/'analysis-voice.wav'
        run([ffmpeg(), '-y', '-v', 'error', '-i', source, '-vn', '-ar', '16000', '-ac', '1', wav])
        print(f'Transcribing locally with {args.model}; first use may download model weights…', flush=True)
        model = WhisperModel(args.model, device='cpu', compute_type='int8', download_root=str(args.runtime/'models'))
        segments, _ = model.transcribe(str(wav), language=None if args.language=='auto' else args.language,
                                        beam_size=5, vad_filter=True, condition_on_previous_text=False, word_timestamps=True)
        cues = []
        for s in segments:
            text = s.text.strip()
            # Model timestamps can extend into padding; clamp drafts to real audio.
            a=max(0.0,s.start); b=min(info['duration'],s.end)
            words=getattr(s,'words',None) or []
            if words:
                group=[]
                for word in words:
                    group.append(word)
                    if len(''.join(w.word for w in group).strip())>=20 or word.word.rstrip().endswith(('。','！','？','.','!','?')):
                        wa=max(0.0,group[0].start); wb=min(info['duration'],group[-1].end); phrase=''.join(w.word for w in group).strip()
                        if phrase and wb>wa: cues.append({'start':wa,'end':wb,'text':phrase})
                        group=[]
                if group:
                    wa=max(0.0,group[0].start); wb=min(info['duration'],group[-1].end); phrase=''.join(w.word for w in group).strip()
                    if phrase and wb>wa: cues.append({'start':wa,'end':wb,'text':phrase})
            elif text and b>a: cues.append({'start': a, 'end': b, 'text': text})
        wav.unlink()
        mode = 'local ASR draft; human listening required'
    for c in cues:
        if not (0<=c['start']<c['end']<=info['duration']+0.1):
            raise ValueError('Transcript time outside source duration; check its clock before selection.')
    (out/'transcript.json').write_text(json.dumps({'status': mode, 'cues': cues}, ensure_ascii=False, indent=2)+'\n')
    write_srt(cues, out/'transcript.srt')
    (out/'transcript.md').write_text('# Source transcript\n\n'+mode+'\n\n'+'\n'.join(f'{stamp(c["start"])}–{stamp(c["end"])}  {c["text"]}' for c in cues)+'\n')
    media = {'master': {'path': str(source)}}
    speaker = args.speaker.resolve() if args.speaker else (source if info['width'] else None)
    if speaker: media['speaker'] = {'path': str(speaker), 'offset': args.speaker_offset}
    if args.screen: media['screen'] = {'path': str(args.screen.resolve()), 'offset': args.screen_offset}
    contact = out/'contact'; contact.mkdir(exist_ok=True)
    if info['width']:
        count = min(12, max(1, math.ceil(info['duration']/30)))
        for i in range(count):
            t = min(info['duration']-0.04, i*info['duration']/count)
            run([ffmpeg(), '-v', 'error', '-y', '-ss', t, '-i', source, '-frames:v', '1', '-vf', 'scale=640:-2', contact/f'{i:02}.jpg'])
    job = {'version': 1, 'sources': media, 'transcript': 'transcript.json', 'speed': 1.0,
           'max_seconds': 90, 'fps': 30, 'speaker_name': '', 'series': '畢業生分享',
           'brand': {'name': 'DotAI'}, 'steps': [], 'cta': '', 'segments': []}
    (out/'job.json').write_text(json.dumps(job, ensure_ascii=False, indent=2)+'\n')
    (out/'media-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2)+'\n')
    print(f'Prepared {len(cues)} cues. Agent: read transcript.md + contact/, fill job.json segments, then render.', flush=True)

def asset(path, base):
    return (base/str(path)).resolve()

def finite(x, name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x): raise ValueError(f'{name} must be a finite number')
    return x

def load_job(path):
    path = Path(path).resolve(); j = json.loads(path.read_text(encoding='utf-8')); base=path.parent
    sources = j.get('sources', {})
    if not sources.get('master'): raise ValueError('sources.master is required')
    for name, src in sources.items():
        if not isinstance(src,dict) or not src.get('path'): raise ValueError(f'Bad source {name}')
        src['file'] = str(asset(src['path'],base)); src['info'] = probe(src['file'])
        finite(src.get('offset',0), f'{name}.offset')
        if name=='master' and not src['info']['audio']: raise ValueError('master must contain original voice')
        crop=src.get('crop')
        if crop:
            if len(crop)!=4 or any(not isinstance(v,int) for v in crop): raise ValueError('crop must be [x,y,width,height] integers')
            x,y,w,h=crop
            if min(x,y)<0 or min(w,h)<=0 or not src['info']['width'] or x+w>src['info']['width'] or y+h>src['info']['height']:
                raise ValueError(f'crop outside {name} image')
    speed = finite(j.get('speed',1), 'speed'); fps = j.get('fps',30)
    if not .5<=speed<=2 or fps not in [24,25,30]: raise ValueError('speed .5–2; fps 24/25/30')
    j['speed']=speed; j['fps']=fps
    limit=finite(j.get('max_seconds',90),'max_seconds')
    if not 0<limit<=600: raise ValueError('max_seconds must be >0 and <=600')
    scene=[]; cursor=0
    if not isinstance(j.get('segments'),list) or not j['segments']: raise ValueError('No segments: agent must select source-linked story cuts first.')
    for i,s in enumerate(j['segments']):
        a=finite(s.get('start'),'start'); b=finite(s.get('end'),'end')
        if not 0<=a<b<=sources['master']['info']['duration']+.02: raise ValueError(f'Segment {i}: master time outside source')
        frames=round((b-a)/speed*fps); d=frames/fps
        if frames<1: raise ValueError('Segment shorter than one frame')
        s=dict(s, id=f'{i:02}', cut_start=cursor, cut_end=cursor+d, duration=d, frames=frames, source_duration=frames/fps*speed)
        s['layout']=s.get('layout','split' if ('screen' in sources or s.get('screen_source')) else 'speaker')
        if s['layout'] not in ['split','speaker']: raise ValueError('layout must be split or speaker')
        for name in ['speaker']+(['screen'] if s['layout']=='split' else []):
            key=s.get(name+'_source',name)
            if key not in sources: raise ValueError(f'{key} video required for {s["layout"]} layout')
            if not sources[key]['info']['width']: raise ValueError(f'{key} is not video')
            s[name+'_key']=key
            t=finite(s.get(name+'_start',a+sources[key].get('offset',0)),name+'_start')
            if t<0 or t+(b-a)>sources[key]['info']['duration']+.02: raise ValueError(f'Segment {i}: {name} sync outside source. offset convention: media_time = master_time + offset.')
            s[name+'_start']=t
        step=s.get('step',0)
        if not isinstance(step,int) or step<0 or (j.get('steps') and step>=len(j['steps'])): raise ValueError('Invalid step index')
        for c in s.get('callouts',[]):
            at=finite(c.get('at',0),'callout.at'); dur=finite(c.get('duration',2),'callout.duration')
            if at<0 or dur<=0 or at>=d: raise ValueError('Callout time outside scene (use final seconds)')
            if c.get('side','left') not in ['left','right']: raise ValueError('Callout side must be left/right')
            if c.get('icon','check') not in ['slides','sheet','cube','check','dashboard','image','web']: raise ValueError('Unknown callout icon')
        scene.append(s); cursor+=d
    if cursor>limit+1e-6: raise ValueError(f'{cursor:.3f}s exceeds {limit}s; reduce cuts, never silently truncate.')
    transcript = read_captions(asset(j['transcript'],base)) if j.get('transcript') else j.get('captions',[])
    if not transcript: raise ValueError('Captions required: supply transcript or timed source captions.')
    for c in transcript:
        a=finite(c.get('start'),'caption.start'); b=finite(c.get('end'),'caption.end')
        if not 0<=a<b<=sources['master']['info']['duration']+.1: raise ValueError('Caption clock is outside master; align transcript before rendering.')
    caps=[]
    for s in scene:
        for c in transcript:
            a=max(s['start'],float(c['start'])); b=min(s['end'],float(c['end']))
            if b>a and c['text'].strip():
                aa=s['cut_start']+(a-s['start'])/speed
                bb=min(s['cut_end'],s['cut_start']+(b-s['start'])/speed)
                if bb>aa: caps.append({'start':aa,'end':bb,'text':str(c['text']), 'scene':s['id'], 'source_start':a,'source_end':b})
    if not caps: raise ValueError('No captions overlap selected cuts; check transcript clock.')
    caps.sort(key=lambda x:x['start'])
    j['scenes']=scene; j['captions_final']=caps; j['duration']=cursor; j['frames']=sum(s['frames'] for s in scene)
    j['width']=1080; j['height']=1920; j['_base']=str(base)
    geo={'screen':[0,410,1080,640],'caption':[0,1050,1080,88],'guest':[0,1138,1080,470],'footer_top':1610,'title_top':213,'workflow_rail_top':340}
    if j.get('layout_preset'):
        preset=json.loads(asset(j['layout_preset'],base).read_text()); geo.update({k:v for k,v in preset.get('layout',{}).items() if k in geo})
    geo.update(j.get('geometry',{}))
    for key in ['screen','caption','guest']:
        box=geo[key]
        if not isinstance(box,list) or len(box)!=4 or any(type(v)!=int for v in box): raise ValueError('Geometry boxes must be [x,y,width,height] integers')
        x,y,w,h=box
        if min(x,y)<0 or min(w,h)<=0 or x+w>1080 or y+h>1920 or w%2 or h%2: raise ValueError('Geometry box outside canvas or has odd dimensions')
    for key in ['footer_top','title_top','workflow_rail_top']:
        if type(geo[key])!=int or not 0<=geo[key]<1920: raise ValueError('Invalid geometry position')
    j['geometry']=geo
    if len(j.get('steps',[]))>7: raise ValueError('Use at most 7 readable steps')
    for key in ['music','logo','header_photo','footer_photo']:
        value=j.get(key) or j.get('brand',{}).get(key)
        if value:
            value=str(asset(value,base))
            if not Path(value).is_file(): raise ValueError(f'Missing {key}')
            j[key+'_file']=value
    for e in j.get('sfx',[]):
        e['file']=str(asset(e['path'],base)); info=probe(e['file'])
        for key in ['at','trim','duration','gain']: finite(e.get(key,0 if key in ['at','trim'] else 1),'sfx.'+key)
        if not info['audio'] or e['at']<0 or e['at']>=cursor or e.get('trim',0)<0 or e.get('duration',1)<=0 or e.get('gain',.2)<0 or e.get('trim',0)+e.get('duration',1)>info['duration']+.02: raise ValueError('Invalid SFX source/range')
    return j

def video_filter(src,w,h,fit,speed,fps):
    crop=src.get('crop'); f=[]
    if crop: x,y,cw,ch=crop; f.append(f'crop={cw}:{ch}:{x}:{y}')
    f.append(f'setpts=(PTS-STARTPTS)/{speed}')
    if fit=='contain': f += [f'scale={w}:{h}:force_original_aspect_ratio=decrease',f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x03131F']
    else: f += [f'scale={w}:{h}:force_original_aspect_ratio=increase',f'crop={w}:{h}']
    f += [f'fps={fps}','setsar=1']
    return ','.join(f)

def make_base(j, work):
    files=[]; originals=[]
    sx,sy,sw,sh=j['geometry']['screen']; gx,gy,gw,gh=j['geometry']['guest']
    for s in j['scenes']:
        cmd=[ffmpeg(),'-v','error','-y','-ss',s['speaker_start'],'-t',s['end']-s['start'],'-i',j['sources'][s['speaker_key']]['file']]
        if s['layout']=='split':
            cmd += ['-ss',s['screen_start'],'-t',s['end']-s['start'],'-i',j['sources'][s['screen_key']]['file']]
            vf=f'[0:v]{video_filter(j["sources"][s["speaker_key"]],gw,gh,"cover",j["speed"],j["fps"])}[guest];[1:v]{video_filter(j["sources"][s["screen_key"]],sw,sh,s.get("screen_fit","contain"),j["speed"],j["fps"])}[proof];color=c=0x03131F:s=1080x1920:r={j["fps"]}:d={s["duration"]}[bg];[bg][proof]overlay={sx}:{sy}[b];[b][guest]overlay={gx}:{gy}[v]'
        else:
            vf=f'[0:v]{video_filter(j["sources"][s["speaker_key"]],1080,1390,"cover",j["speed"],j["fps"])}[guest];color=c=0x03131F:s=1080x1920:r={j["fps"]}:d={s["duration"]}[bg];[bg][guest]overlay=0:310[v]'
        dest=work/f'{s["id"]}-picture.mp4'
        cmd += ['-filter_complex',vf,'-map','[v]','-an','-frames:v',s['frames'],'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',dest]
        run(cmd); files.append(dest)
        voice=work/f'{s["id"]}-voice.wav'
        run([ffmpeg(),'-v','error','-y','-ss',s['start'],'-t',s['end']-s['start'],'-i',j['sources']['master']['file'],'-vn','-af',f'atempo={j["speed"]},apad','-t',s['duration'],'-ar','48000','-ac','1',voice])
        originals.append(voice)
        print(f'Prepared scene {s["id"]}: {s["duration"]:.2f}s',flush=True)
    # Generated simple filenames avoid concat escaping problems on user input paths.
    for paths,ext in [(files,'mp4'),(originals,'wav')]:
        listing=work/f'concat-{ext}.txt'; listing.write_text(''.join(f"file '{f.name}'\n" for f in paths))
        dest=work/('base.mp4' if ext=='mp4' else 'voice.wav')
        run([ffmpeg(),'-v','error','-y','-f','concat','-safe','0','-i',listing,'-c','copy',dest])
    return work/'base.mp4',work/'voice.wav'

def uri(path):
    ext=Path(path).suffix.lower(); mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml','.ttf':'font/ttf','.woff':'font/woff','.webp':'image/webp'}.get(ext,'application/octet-stream')
    return 'data:'+mime+';base64,'+base64.b64encode(Path(path).read_bytes()).decode()

def create_html(j, runtime, out):
    data={k:j.get(k) for k in ['speaker_name','series','cta','steps','scenes','captions_final','duration','brand','geometry']}
    for key in ['logo','header_photo','footer_photo']:
        if j.get(key+'_file'): data[key]=uri(j[key+'_file'])
    template=(ROOT/'assets/overlay.html').read_text(encoding='utf-8')
    template=template.replace('__FONT__',uri(runtime/'NotoSansTC.ttf'))
    # Escape script terminators so titles/captions remain data, never HTML/JS.
    template=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026'))
    (out/'overlay.html').write_text(template,encoding='utf-8')
    return out/'overlay.html'

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

class LocalServer:
    def __init__(self,directory):
        handler=functools.partial(QuietHandler,directory=str(directory))
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        return f'http://127.0.0.1:{self.server.server_port}'
    def __exit__(self,*args):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

def render(args):
    j=load_job(args.job); out=args.output.resolve()
    if (out/'final.mp4').exists() and not args.overwrite: raise ValueError('Output exists. Choose a new output directory or use --overwrite.')
    out.mkdir(parents=True,exist_ok=True); work=out/'.work'; work.mkdir(exist_ok=True)
    base,voice=make_base(j,work)
    from sound import attach
    attach(j,work)
    if args.keep_pairs:
        pairs=out/'pairs'; pairs.mkdir(exist_ok=True)
        staged=pairs/'.staging';staged.mkdir(exist_ok=True)
        selected={'speaker':[]}
        if any(scene['layout']=='split' for scene in j['scenes']):selected['screen']=[]
        for scene in j['scenes']:
            for name in selected:
                key=scene.get(name+'_key',name)
                if key not in j['sources']:
                    key=next(c[name+'_key'] for c in j['scenes'] if c.get(name+'_key'))
                src=j['sources'][key]; t=scene.get(name+'_start',scene['start']+src.get('offset',0))
                source_length=scene['end']-scene['start']
                if t<0 or t+source_length>src['info']['duration']+.02:
                    # A speaker-only Hook can precede a screen recording. Keep blank proof explicit.
                    info=src['info']; crop=src.get('crop'); w,h=(crop[2],crop[3]) if crop else (info['width'],info['height'])
                    scale=min(1,1920/w,1080/h); w=2*int(w*scale/2); h=2*int(h*scale/2)
                    cmd=[ffmpeg(),'-v','error','-y','-f','lavfi','-i',f'color=c=0x03131F:s={w}x{h}:r={j["fps"]}']
                    vf=f'fps={j["fps"]}'
                else:
                    cmd=[ffmpeg(),'-v','error','-y','-ss',t,'-t',source_length,'-i',src['file']]
                    f=[]
                    if src.get('crop'):
                        x,y,w,h=src['crop'];f.append(f'crop={w}:{h}:{x}:{y}')
                    w,h=(1920,1080) if name=='screen' else (1080,1920)
                    f += [f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2',f'setpts=(PTS-STARTPTS)/{j["speed"]}',f'fps={j["fps"]}','setsar=1']
                    vf=','.join(f)
                dest=staged/f'{scene["id"]}-{name}.mp4'
                cmd+=['-vf',vf,'-an','-frames:v',scene['frames'],'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',dest]
                run(cmd);selected[name].append(dest)
            run([ffmpeg(),'-v','error','-y','-i',staged/f'{scene["id"]}-speaker.mp4','-i',work/f'{scene["id"]}-voice.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-t',scene['duration'],pairs/f'{scene["id"]}-A-speaker-with-voice.mp4'])
            if 'screen' in selected:
                shutil.copy2(staged/f'{scene["id"]}-screen.mp4',pairs/f'{scene["id"]}-B-screen-silent.mp4')
        index='# 配對素材｜同編號、同長度\n\n| 編號／章節 | 秒數 | A真人有聲 | B螢幕無聲 |\n| --- | --- | --- | --- |\n'
        for scene in j['scenes']:
            sid=scene['id'];title=scene.get('title','').replace('|','／').replace('\n',' ')
            b=f'[{sid}-B-screen-silent.mp4]({sid}-B-screen-silent.mp4)' if 'screen' in selected else '此段沒有螢幕素材'
            index+=f'| {sid} · {title} | {scene["duration"]:.3f} | [{sid}-A-speaker-with-voice.mp4]({sid}-A-speaker-with-voice.mp4) | {b} |\n'
        (pairs/'INDEX.md').write_text(index,encoding='utf-8')
        kit=out/'rebuild';kit.mkdir(exist_ok=True)
        kit_sources={'master':{'path':'voice.wav'}}
        shutil.copy2(voice,kit/'voice.wav')
        for name,paths in selected.items():
            for i,file in enumerate(paths):
                dest=f'{name}-{i:02}.mp4';shutil.copy2(file,kit/dest)
                kit_sources[f'{name}_{i:02}']={'path':dest}
        source_job=json.loads(Path(args.job).read_text())
        source_job.pop('layout_preset',None)
        source_job.update(sources=kit_sources,transcript='captions.json',speed=1.0,geometry=j['geometry'],segments=[])
        for i,scene in enumerate(j['scenes']):
            cut={k:v for k,v in scene.items() if k in ['title','step','layout','screen_fit','source_label','callouts','stats']}
            cut.update(start=scene['cut_start'],end=scene['cut_end'],speaker_source=f'speaker_{i:02}',speaker_start=0)
            if scene['layout']=='split':cut.update(screen_source=f'screen_{i:02}',screen_start=0)
            source_job['segments'].append(cut)
        # Caption time is already the final media clock; never speed this selected kit twice.
        (kit/'captions.json').write_text(json.dumps(j['captions_final'],ensure_ascii=False,indent=2)+'\n')
        for key in ['music','logo','header_photo','footer_photo']:
            if j.get(key+'_file'):
                dest=key+Path(j[key+'_file']).suffix;shutil.copy2(j[key+'_file'],kit/dest);source_job[key]=dest
                source_job.get('brand',{}).pop(key,None)
        source_job['sfx']=[{k:v for k,v in event.items() if k!='file'} for event in j.get('sfx',[])]
        source_job['auto_music']=False;source_job['auto_sfx']=False;source_job['music_gain']=j.get('music_gain',.12)
        for i,event in enumerate(j.get('sfx',[])):
            dest=f'sfx-{i}'+Path(event['file']).suffix;shutil.copy2(event['file'],kit/dest);source_job['sfx'][i]['path']=dest
        (kit/'job.json').write_text(json.dumps(source_job,ensure_ascii=False,indent=2)+'\n')
        (kit/'README.md').write_text('Selected-footage rebuild kit. Sources are cropped and already speed-adjusted; speed=1.0. Full original recordings remain outside this kit.\n\nFrom an installed Skill run: python3 scripts/run.py render --job /path/to/rebuild/job.json --output /new/output --keep-pairs\n',encoding='utf-8')
    html_path=create_html(j,args.runtime,out)
    cmd=[ffmpeg(),'-v','error','-y','-f','image2pipe','-framerate',j['fps'],'-i','pipe:0','-i',base,'-i',voice]
    mixes=['[2:a]loudnorm=I=-18:TP=-2:LRA=7,aresample=48000[voice]']; added=[]; n=3
    if j.get('music_file'):
        cmd+=['-stream_loop','-1','-i',j['music_file']]
        gain=finite(j.get('music_gain',.12),'music_gain')
        if not 0<=gain<=1: raise ValueError('music_gain must be 0–1')
        fade=min(1.5,j['duration']/3)
        mixes+=[f'[{n}:a]atrim=duration={j["duration"]},asetpts=PTS-STARTPTS,volume={gain},afade=t=in:d={fade},afade=t=out:st={j["duration"]-fade}:d={fade}[music]']; added.append('[music]'); n+=1
    if j.get('sfx'):
        for i,e in enumerate(j['sfx']):
            cmd+=['-i',e['file']]; trim=e.get('trim',0); length=e.get('duration',1); delay=round(e['at']*1000)
            mixes+=[f'[{n}:a]atrim=start={trim}:duration={length},asetpts=PTS-STARTPTS,volume={e.get("gain",.2)},afade=t=out:st={max(0,length-.3)}:d={min(.3,length)},adelay={delay}:all=1[sfx{i}]']; added.append(f'[sfx{i}]'); n+=1
    if added:
        mixes+=['[voice]asplit=2[vmain][duckkey]', ''.join(added)+f'amix=inputs={len(added)}:duration=longest:normalize=0[bed]',
                '[bed][duckkey]sidechaincompress=threshold=0.03:ratio=5:attack=10:release=200[ducked]',
                '[vmain][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=0[a]']
    else: mixes+=['[voice]alimiter=limit=0.89:level=0[a]']
    filters='[1:v][0:v]overlay=0:0:shortest=1,format=yuv420p[v];'+';'.join(mixes)
    temp=out/'final.partial.mp4'
    cmd+=['-filter_complex',filters,'-map','[v]','-map','[a]','-frames:v',j['frames'],'-t',j['duration'],'-c:v','libx264','-preset','veryfast','-crf',args.crf,'-c:a','aac','-ar','48000','-b:a','192k','-movflags','+faststart',temp]
    log=open(work/'encode.log','w')
    proc=subprocess.Popen([str(x) for x in cmd],stdin=subprocess.PIPE,stderr=log,stdout=subprocess.DEVNULL)
    try:
        with LocalServer(out) as server, browser(args.runtime) as p:
            b=p.chromium.launch(); page=b.new_page(viewport={'width':1080,'height':1920},device_scale_factor=1)
            page.goto(server+'/overlay.html'); page.evaluate('document.fonts.ready'); page.wait_for_function('window.ready === true')
            for frame in range(j['frames']):
                page.evaluate('(t)=>window.seek(t)',frame/j['fps'])
                png=page.screenshot(omit_background=True)
                proc.stdin.write(png)
                if frame%j['fps']==0: print(f'HTML render {frame}/{j["frames"]} frames',flush=True)
            b.close()
        proc.stdin.close(); rc=proc.wait()
        if rc: raise ValueError('MP4 encoding failed: '+(work/'encode.log').read_text()[-3500:])
    except BaseException:
        if proc.poll() is None: proc.kill(); proc.wait()
        raise
    finally: log.close()
    temp.replace(out/'final.mp4')
    info=probe(out/'final.mp4')
    if info['width']!=1080 or info['height']!=1920 or abs(info['duration']-j['duration'])>.15 or not info['audio']:
        raise ValueError('Output dimension, duration or audio check failed')
    decode=run([ffmpeg(),'-v','error','-i',out/'final.mp4','-progress','pipe:1','-nostats','-f','null','-'])
    decoded_frames=int(re.findall(r'(?m)^frame=(\d+)',decode)[-1])
    if decoded_frames!=j['frames']: raise ValueError('Decoded frame count differs from the plan')
    write_srt(j['captions_final'],out/'captions.srt')
    (out/'cut-map.json').write_text(json.dumps({'fps':j['fps'],'speed':j['speed'],'duration':j['duration'],'frames':j['frames'],'scenes':j['scenes']},ensure_ascii=False,indent=2)+'\n')
    (out/'captions.json').write_text(json.dumps(j['captions_final'],ensure_ascii=False,indent=2)+'\n')
    story='# Selected story / source cuts\n\n'+''.join(f'## {stamp(s["cut_start"])}–{stamp(s["cut_end"])} | {s.get("title","")}\n\nSource: {stamp(s["start"])}–{stamp(s["end"])}\n\n'+ '\n'.join(c['text'] for c in j['captions_final'] if c['scene']==s['id'])+'\n\n' for s in j['scenes'])
    (out/'story.md').write_text(story,encoding='utf-8')
    # Keep input plan for recutting with the original sources; overlay+base permit local visual review.
    shutil.copy2(args.job,out/'job-source.json')
    (out/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Reels review</title><style>body{background:#03131f;color:white;font:16px sans-serif}video{height:90vh;max-width:100%}</style><video controls src="final.mp4"></video><p>Original speech and caption accuracy require listening review.</p>')
    versions={}
    import importlib.metadata
    for name in ['playwright','imageio-ffmpeg']:
        versions[name]=importlib.metadata.version(name)
    receipt={'status':'rendered-and-decoded','width':1080,'height':1920,'fps':j['fps'],'frames':j['frames'],'decoded_frames':decoded_frames,'duration':j['duration'],'caption_cues':len(j['captions_final']),
             'sha256':hashlib.sha256((out/'final.mp4').read_bytes()).hexdigest(),'versions':versions,'speech_human_listened':False,'published':False,
             'rebuild':'rebuild/job.json contains relative, selected, cropped, speed-adjusted media when --keep-pairs is enabled. Original recovery and new selections need the full sources.' if args.keep_pairs else 'Original sources are needed; use --keep-pairs to save a portable selected-footage kit.'}
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(f'DONE: {out/"final.mp4"} ({j["duration"]:.3f}s)',flush=True)

def validate(args):
    j=load_job(args.job)
    print(json.dumps({'valid':True,'duration':j['duration'],'frames':j['frames'],'caption_cues':len(j['captions_final']),'scenes':len(j['scenes'])},indent=2))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runtime',type=Path,default=ROOT/'.runtime')
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    p=sub.add_parser('frames');p.add_argument('--source',type=Path,required=True);p.add_argument('--times',type=float,nargs='+',required=True);p.add_argument('--crop',type=int,nargs=4);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('sync'); p.add_argument('--master',type=Path,required=True); p.add_argument('--secondary',type=Path,required=True); p.add_argument('--window',type=float,default=180); p.add_argument('--max-offset',type=float,default=120); p.add_argument('--output',type=Path)
    p=sub.add_parser('prepare'); p.add_argument('--source',type=Path,required=True); p.add_argument('--speaker',type=Path); p.add_argument('--screen',type=Path)
    p.add_argument('--speaker-offset',type=float,default=0); p.add_argument('--screen-offset',type=float,default=0); p.add_argument('--transcript',type=Path)
    p.add_argument('--model',default='small'); p.add_argument('--language',default='auto'); p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('validate'); p.add_argument('--job',type=Path,required=True)
    p=sub.add_parser('render'); p.add_argument('--job',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--overwrite',action='store_true'); p.add_argument('--keep-pairs',action='store_true'); p.add_argument('--crf',type=int,default=20)
    args=ap.parse_args(); args.runtime=args.runtime.resolve()
    try: globals()[args.command](args)
    except (ValueError,ImportError,OSError,subprocess.CalledProcessError) as e: ap.exit(2,str(e)+'\n')

if __name__=='__main__': main()
