"""Source/clock/claim-data safeguards and actual media-plan invariants."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reels
ROOT=Path(__file__).resolve().parents[1]

class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.p=Path(cls.tmp.name)
        reels.run([reels.ffmpeg(),'-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-f','lavfi','-i','sine=frequency=330:sample_rate=48000','-t','4','-c:v','libx264','-preset','ultrafast','-c:a','aac',cls.p/'source.mp4'])
        reels.run([reels.ffmpeg(),'-v','error','-y','-i',cls.p/'source.mp4','-an','-c:v','copy',cls.p/'silent.mp4'])
        cls.job={'sources':{'master':{'path':'source.mp4'},'speaker':{'path':'source.mp4'},'screen':{'path':'silent.mp4'}},'speed':1.1,'fps':30,'max_seconds':90,
          'segments':[{'start':1.0,'end':3.2,'layout':'split','title':'Output'}],
          'captions':[{'start':0.5,'end':2.0,'text':'完整字幕'},{'start':2.0,'end':3.8,'text':'不可省略'}]}
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def plan(self,j=None):
        (self.p/'job.json').write_text(json.dumps(j or self.job,ensure_ascii=False))
        return reels.load_job(self.p/'job.json')
    def test_speed_and_caption_clock(self):
        j=self.plan();self.assertEqual(j['frames'],60);self.assertEqual(j['duration'],2)
        self.assertEqual(len(j['captions_final']),2);self.assertEqual(j['captions_final'][0]['start'],0)
        self.assertAlmostEqual(j['captions_final'][0]['end'],1/1.1);self.assertEqual(j['captions_final'][-1]['end'],2)
    def test_no_silent_master(self):
        j=copy.deepcopy(self.job);j['sources']['master']['path']='silent.mp4'
        with self.assertRaisesRegex(ValueError,'original voice'):self.plan(j)
    def test_reject_out_of_source(self):
        j=copy.deepcopy(self.job);j['segments'][0]['end']=8
        with self.assertRaisesRegex(ValueError,'outside source'):self.plan(j)
    def test_reject_invalid_sync(self):
        j=copy.deepcopy(self.job);j['sources']['screen']['offset']=-2
        with self.assertRaisesRegex(ValueError,'sync outside'):self.plan(j)
    def test_offset_convention(self):
        j=copy.deepcopy(self.job);j['sources']['screen']['offset']=.4
        self.assertAlmostEqual(self.plan(j)['scenes'][0]['screen_start'],1.4)
    def test_per_scene_mapping(self):
        j=copy.deepcopy(self.job);j['sources']['screen']['offset']=-2;j['segments'][0]['screen_start']=.2
        self.assertAlmostEqual(self.plan(j)['scenes'][0]['screen_start'],.2)
    def test_reject_bad_crop(self):
        j=copy.deepcopy(self.job);j['sources']['speaker']['crop']=[300,0,100,180]
        with self.assertRaisesRegex(ValueError,'crop outside'):self.plan(j)
    def test_no_silent_truncation(self):
        j=copy.deepcopy(self.job);j['max_seconds']=1.5
        with self.assertRaisesRegex(ValueError,'exceeds'):self.plan(j)
    def test_missing_captions(self):
        j=copy.deepcopy(self.job);j['captions']=[]
        with self.assertRaisesRegex(ValueError,'Captions required'):self.plan(j)
    def test_srt_multiline_roundtrip(self):
        cue=[{'start':1.23,'end':4.56,'text':'第一行\n第二行'}]
        reels.write_srt(cue,self.p/'a.srt');self.assertEqual(reels.read_captions(self.p/'a.srt'),cue)
    def test_vtt_minute_clock(self):
        (self.p/'a.vtt').write_text('WEBVTT\n\n00:02.000 --> 00:03.000\n測試\n')
        self.assertEqual(reels.read_captions(self.p/'a.vtt')[0]['start'],2)
    def test_nan_rejected(self):
        j=copy.deepcopy(self.job);j['speed']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):self.plan(j)
    def test_unselected_story_not_rendered(self):
        j=copy.deepcopy(self.job);j['segments']=[]
        with self.assertRaisesRegex(ValueError,'agent must select'):self.plan(j)
    def test_multiple_camera_sources(self):
        j=copy.deepcopy(self.job);j['sources']['camera2']=j['sources'].pop('speaker');j['segments'][0]['speaker_source']='camera2'
        self.assertEqual(self.plan(j)['scenes'][0]['speaker_key'],'camera2')
    def test_custom_geometry(self):
        j=copy.deepcopy(self.job);j['geometry']={'guest':[0,1200,1080,400]}
        self.assertEqual(self.plan(j)['geometry']['guest'],[0,1200,1080,400])
    def test_geometry_outside_canvas(self):
        j=copy.deepcopy(self.job);j['geometry']={'screen':[0,410,1200,640]}
        with self.assertRaisesRegex(ValueError,'Geometry box outside'):self.plan(j)
    def test_caption_wrong_clock(self):
        j=copy.deepcopy(self.job);j['captions'][0]['end']=30
        with self.assertRaisesRegex(ValueError,'Caption clock'):self.plan(j)
    def test_text_is_data_not_html(self):
        j=self.plan();j['scenes'][0]['title']='</script><script>window.pwned=1</script>'
        f=reels.create_html(j,ROOT/'.runtime',self.p);text=f.read_text()
        self.assertNotIn('</script><script>window.pwned',text)
        self.assertIn('\\u003c/script\\u003e',text)

if __name__=='__main__':unittest.main()
