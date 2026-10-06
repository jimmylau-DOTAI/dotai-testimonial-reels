"""Original procedural ambience and restrained motion accents; no external samples."""
import wave
from pathlib import Path

def save(path, samples, sr=48000):
    import numpy as np
    samples=np.clip(samples,-.95,.95)
    if samples.ndim==1:samples=np.column_stack([samples,samples])
    with wave.open(str(path),'wb') as f:
        f.setparams((2,2,sr,len(samples),'NONE','not compressed'))
        f.writeframes((samples*32767).astype('<i2').tobytes())

def ambience(path, seconds):
    import numpy as np
    sr=48000;n=round(seconds*sr);audio=np.zeros(n);chords=[(130.81,164.81,196),(110,130.81,164.81),(87.31,110,130.81),(98,123.47,146.83)]
    for k,start in enumerate(range(0,n,4*sr)):
        count=min(5*sr,n-start);t=np.arange(count)/sr;fade=np.minimum(1,t/1.2)*np.minimum(1,(count/sr-t)/1.2)
        for f in chords[k%len(chords)]:audio[start:start+count]+=.028*np.sin(2*np.pi*f*t)*fade
    save(path,audio)

def accent(path, kind):
    import numpy as np
    sr=48000;t=np.arange(round(.5*sr))/sr
    if kind=='hit':s=(.42*np.sin(2*np.pi*(110*t-55*t*t))+.06*np.sin(2*np.pi*750*t))*np.exp(-t*13)
    elif kind=='counter':s=np.zeros_like(t)
    else:
        rng=np.random.default_rng(11);noise=rng.normal(0,1,len(t));low=np.convolve(noise,np.ones(9)/9,mode='same');s=(noise-low)*np.sin(np.pi*t/.5)**2*.14
    if kind=='counter':
        for at in [.05,.16,.28]:
            tau=t-at;mask=(tau>=0)&(tau<.08);s[mask]+=.2*np.sin(2*np.pi*1200*tau[mask])*np.exp(-tau[mask]*65)
    save(path,s)


def attach(job, work):
    duration=job['duration']
    if not job.get('music_file') and job.get('auto_music',True):
        dest=work/'generated-ambience.wav';ambience(dest,duration);job['music_file']=str(dest);job['music_gain']=job.get('music_gain',.32)
    if job.get('sfx') or not job.get('auto_sfx',True):return
    kinds={}
    for kind in ['hit','whoosh','counter']:
        f=work/f'generated-{kind}.wav';accent(f,kind);kinds[kind]=str(f)
    events=[{'file':kinds['hit'],'path':kinds['hit'],'at':min(.1,duration/4),'duration':min(.5,duration*.5),'gain':.2}]
    for scene in job['scenes']:
        if scene.get('callouts'):
            at=scene['cut_start']+min(c.get('at',0) for c in scene['callouts'])
            events.append({'file':kinds['whoosh'],'path':kinds['whoosh'],'at':at,'duration':min(.5,duration-at),'gain':.12})
        if scene.get('stats') and scene['duration']>.8:
            at=scene['cut_start']+.7;events.append({'file':kinds['counter'],'path':kinds['counter'],'at':at,'duration':min(.5,duration-at),'gain':.16})
    job['sfx']=events;job['generated_audio']=True
