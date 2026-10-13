import json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
try:import boto3
except ModuleNotFoundError:
    sys.modules['boto3']=types.SimpleNamespace(client=Mock())
    class ClientError(Exception):
        def __init__(self,response,operation):self.response=response
    sys.modules['botocore']=types.ModuleType('botocore')
    sys.modules['botocore.exceptions']=types.SimpleNamespace(ClientError=ClientError)
import upload_podcast

class UploadTests(unittest.TestCase):
    def test_both_feeds_preserve_guid_save_vtt_and_repeat_without_upload(self):
        with tempfile.TemporaryDirectory() as folder:
            old=os.getcwd();os.chdir(folder)
            try:
                Path('data').mkdir();Path('vtt/2026').mkdir(parents=True);Path('vtt/2026/25-170.vtt').write_text('WEBVTT\n')
                Path('commit_message.txt').write_text('Alignment chapters for 25-170.')
                case={'name':'Example','description':'Facts','date_argued_timestamp':1791158400,'mp3_length':30,'mp3_size':123,'b2_url':'https://podcast.scotusstats.com/2026/25-170.mp3','media_revision':'new','media_uploaded_revision':'old','chapters':[{'start':0,'title':'Advocate'},{'start':5,'title':'Justice Thomas'}]}
                Path('data/case_data.json').write_text(json.dumps({'2026':{'25-170':case}}))
                with patch('upload_podcast.upload_to_r2') as media,patch('upload_podcast.upload_rss') as rss:
                    upload_podcast.build_podcast();upload_podcast.build_podcast(spotify=True)
                    self.assertEqual(media.call_count,2);self.assertEqual(rss.call_count,2)
                    data=json.loads(Path('data/case_data.json').read_text());self.assertEqual(data['2026']['25-170']['media_uploaded_revision'],'new');self.assertIn('vtt_url',data['2026']['25-170'])
                    self.assertIn('<guid>scotus_2026_25-170_v0</guid>',Path('data/podcast.rss').read_text())
                    self.assertIn('00:00:05 Justice Thomas',Path('data/podcast_spotify.rss').read_text())
                    media.reset_mock();rss.reset_mock();upload_podcast.build_podcast();upload_podcast.build_podcast(spotify=True)
                    media.assert_not_called();rss.assert_not_called()
            finally:os.chdir(old)

    def test_r2_reconciles_uploaded_revision_before_retransmitting(self):
        client=Mock();client.head_object.return_value={'Metadata':{'media-revision':'same'}}
        with patch.dict(os.environ,{'R2_ENDPOINT':'https://example.invalid','R2_ACCESS_KEY':'test','R2_SECRET_KEY':'test'}),patch('upload_podcast.boto3.client',return_value=client):
            upload_podcast.upload_to_r2('file.mp3','2026/case.mp3','same')
        client.upload_file.assert_not_called()

if __name__=='__main__':unittest.main()
