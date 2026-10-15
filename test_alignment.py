import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chapter_tools import build_chapters
from get_alignment import apply_recording
from get_oyez import update_description

def fixture():
    advocate={'name':'Jane Doe','last_name':'Doe','kind':'advocate','role':'for petitioner'}
    justice={'name':'Clarence Thomas','last_name':'Thomas','kind':'justice'}
    def turn(person,start,stop):return {'speaker':person,'start':start,'stop':stop,'text_blocks':[{'text':'These are sufficiently many spoken words to count as a substantive turn.','start':start,'stop':stop}]}
    return {'schema_version':1,'recording_id':'2026-10-05-25-170-argument-1','term':'2026','docket':'25-170','argument_date':'2026-10-05','case_name':'Example v. Case','audio':{'duration_seconds':30,'sha256':'a'*64,'url':'https://www.supremecourt.gov/example.mp3'},
            'sections':[{'turns':[turn(advocate,0,5),turn(justice,5,10),turn(advocate,10,15),turn(justice,15,20),turn(advocate,20,30)]}]}

class AlignmentTests(unittest.TestCase):
    def entry(self,r):return {key:r[key] for key in ('recording_id','term','docket')}|{'revision':'b'*64}

    def test_existing_chapter_labels_and_repeated_justice_filter(self):
        r=fixture();chapters=build_chapters(r['sections'],{'Jane Doe':'Jane Doe (for petitioner)'},{'Clarence Thomas':r['sections'][0]['turns'][1]['speaker']})
        self.assertEqual(chapters,[{'title':'Jane Doe (for petitioner)','start':0},{'title':'Doe - Justice Thomas','start':5}])

    def test_alignment_upgrade_preserves_description_guid_fields_and_is_idempotent(self):
        r=fixture();data={'2026':{'25-170':{'description':'Oyez facts','description_source':'oyez','b2_url':'https://podcast.scotusstats.com/2026/25-170.mp3','date_argued_timestamp':1791158400}}}
        with tempfile.TemporaryDirectory() as folder,patch('get_alignment.obtain_audio',side_effect=lambda r,p:p.write_bytes(b'audio')),patch('get_alignment.write_chapter_tags',return_value=123),patch('get_alignment.build_vtt_transcript'):
            old=os.getcwd();os.chdir(folder)
            try:
                apply_recording(data,self.entry(r),r)
                record=data['2026']['25-170'];self.assertEqual(record['description'],'Oyez facts');self.assertEqual(record['b2_url'],'https://podcast.scotusstats.com/2026/25-170.mp3');self.assertEqual(record['mp3_size'],123)
                self.assertIsNone(apply_recording(data,self.entry(r),r))
                later={**self.entry(r),'revision':'c'*64};self.assertIsNotNone(apply_recording(data,later,r));self.assertEqual(len(data['2026']),1)
            finally:os.chdir(old)

    def test_dry_run_downloads_no_audio_and_does_not_change_state(self):
        r=fixture();data={};before=copy.deepcopy(data)
        with patch('get_alignment.obtain_audio') as audio:
            result=apply_recording(data,self.entry(r),r,dry_run=True)
        audio.assert_not_called();self.assertEqual(data,before);self.assertTrue(result['chapters'])

    def test_metadata_update_keeps_alignment_and_media_revision(self):
        record={'date_argued_timestamp':1234567,'alignment_source':'scotus_ctc','media_revision':'keep','alignment_revision':'keep','chapters':[{'start':5,'title':'Thomas'}]}
        metadata={'timeline':[{'event':'Granted','dates':[100]}],'facts_of_the_case':'Facts'}
        with patch('get_oyez.build_description',return_value='Oyez updated facts') as description:
            self.assertTrue(update_description(record,metadata));self.assertFalse(update_description(record,metadata))
        self.assertEqual(record['alignment_revision'],'keep');self.assertEqual(record['media_revision'],'keep');self.assertEqual(description.call_count,1)

    def test_multiple_hearings_do_not_silently_replace_episode(self):
        r=fixture();data={'2026':{'25-170':{'argument_date':'2026-10-01'}}}
        self.assertIsNone(apply_recording(data,self.entry(r),r,dry_run=True))

class ArtworkTests(unittest.TestCase):
    def test_index_artwork_without_rewriting_transcript(self):
        r=fixture();r['alignment_revision']='a'*64
        entry={key:r[key] for key in ('recording_id','term','docket')}|{'revision':'b'*64,'artwork_sha256':'c'*64,'artwork_url':'https://scotusstats.com/podcast/alignment/case-'+('c'*64)+'.jpg'}
        data={'2026':{'25-170':{'alignment_revision':'a'*64,'chapters':[]}}}
        with patch('get_alignment.obtain_audio') as audio,patch('get_alignment.write_chapter_tags') as tags:
            result=apply_recording(data,entry,r)
        self.assertTrue(result['artwork_only']);audio.assert_not_called();tags.assert_not_called()
        self.assertEqual(data['2026']['25-170']['artwork_url'],entry['artwork_url'])

    def test_artwork_only_revision_never_retags_audio(self):
        r=fixture();r['alignment_revision']='a'*64;r['artwork']={'sha256':'c'*64}
        entry={key:r[key] for key in ('recording_id','term','docket')}|{'revision':'b'*64,'artwork_sha256':'c'*64,'artwork_url':'https://scotusstats.com/podcast/alignment/case.jpg'}
        data={'2026':{'25-170':{'alignment_revision':'a'*64,'media_revision':'keep','chapters':[{'title':'Jane','start':0}]}}}
        with patch('get_alignment.obtain_audio') as audio,patch('get_alignment.write_chapter_tags') as tags:
            result=apply_recording(data,entry,r)
            self.assertTrue(result['artwork_only']);audio.assert_not_called();tags.assert_not_called()
            self.assertEqual(data['2026']['25-170']['media_revision'],'keep')
            self.assertEqual(data['2026']['25-170']['artwork_url'],entry['artwork_url'])
            self.assertIsNone(apply_recording(data,entry,r))

if __name__=='__main__':unittest.main()
