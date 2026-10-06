#!/usr/bin/env python3
"""Generate fictional media and run the real renderer; no student content required."""
import argparse,json,subprocess,sys
from pathlib import Path
from reels import ffmpeg,run,browser
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'.demo');p.add_argument('--no-render',action='store_true');args=p.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    # All pictures, captions and audio are generated test fixtures, not testimonials.
    with browser(ROOT/'.runtime') as pw:
        b=pw.chromium.launch();page=b.new_page(viewport={'width':1280,'height':720})
        page.set_content('<style>body{margin:0;background:#eaf2fc;font:28px sans-serif;color:#123}header{padding:35px;background:#0b2c4e;color:white}main{padding:40px}table{width:95%;border-collapse:collapse}td{border:2px solid #b7c9df;padding:18px}</style><header>FICTIONAL DEMO · Proposal worksheet</header><main><h1>Input → draft → review</h1><table><tr><td>Item</td><td>Quantity</td><td>Estimate</td></tr><tr><td>Design draft</td><td>3</td><td>Demo only</td></tr><tr><td>Presentation</td><td>1</td><td>Demo only</td></tr></table></main>')
        page.screenshot(path=str(out/'screen.png'));b.close()
    run([ffmpeg(),'-v','error','-y','-f','lavfi','-i','testsrc2=size=960x540:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','8','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac',out/'master.mp4'])
    run([ffmpeg(),'-v','error','-y','-loop','1','-i',out/'screen.png','-t','8','-vf','zoompan=z=1+0.0001*on:x=0:y=0:d=1:s=1280x720:fps=30','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',out/'screen.mp4'])
    run([ffmpeg(),'-v','error','-y','-f','lavfi','-i','sine=frequency=180:sample_rate=48000','-t','8','-af','volume=0.03',out/'music.wav'])
    run([ffmpeg(),'-v','error','-y','-f','lavfi','-i','sine=frequency=800:sample_rate=48000','-t','0.5','-af','afade=t=out:st=0.05:d=0.45',out/'hit.wav'])
    cues=[{'start':0,'end':2,'text':'示例字幕：先看實際成果。'},{'start':2,'end':4,'text':'示例字幕：AI 準備，人作判斷。'},{'start':4,'end':7,'text':'示例字幕：整理提案與報價。'}]
    (out/'transcript.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2)+'\n')
    job={'version':1,'sources':{'master':{'path':'master.mp4'},'speaker':{'path':'master.mp4'},'screen':{'path':'screen.mp4'}},'transcript':'transcript.json','speed':1.1,'fps':30,'max_seconds':90,
      'speaker_name':'示例人物','series':'示例分享 · 非真實好評','brand':{'name':'DotAI','series':'AI Agent 工作流'},'steps':['AI 初稿','人工覆核','提案報價'],'cta':'測試素材 · [[非真實好評]]',
      'music':'music.wav','music_gain':.18,'sfx':[{'path':'hit.wav','at':0.5,'trim':0,'duration':.5,'gain':.12}],
      'segments':[{'start':0,'end':2.2,'layout':'speaker','title':'AI 準備，人作判斷','step':0,'stats':[{'value':'DEMO','label':'示例動畫'}]},
                  {'start':2.2,'end':4.4,'layout':'split','title':'完整流程，看得見轉變','step':1,'callouts':[{'at':.2,'duration':1.6,'side':'left','icon':'check','text':'人工覆核'},{'at':.3,'duration':1.6,'side':'right','icon':'dashboard','text':'工作流程'}]},
                  {'start':4.4,'end':6.6,'layout':'split','title':'提案與報價，清楚交付','step':2,'callouts':[{'at':.2,'duration':1.6,'side':'left','icon':'slides','text':'Proposal'},{'at':.3,'duration':1.6,'side':'right','icon':'sheet','text':'Excel 報價'}]}]}
    (out/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2)+'\n')
    if not args.no_render:
        subprocess.run([sys.executable,str(ROOT/'scripts/reels.py'),'render','--job',str(out/'job.json'),'--output',str(out/'render'),'--keep-pairs','--overwrite'],check=True)
    print('Generated fictional demo at',out)

if __name__=='__main__':main()
