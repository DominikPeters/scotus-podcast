import sys,types,unittest
from unittest.mock import Mock
try:import boto3
except ModuleNotFoundError:
 sys.modules['boto3']=types.SimpleNamespace(client=Mock());sys.modules['botocore']=types.ModuleType('botocore');sys.modules['botocore.exceptions']=types.SimpleNamespace(ClientError=Exception)
from get_youtube import apply_links
from upload_podcast import description_with_video
class YouTubeTests(unittest.TestCase):
 def test_exact_date_match_and_idempotency(self):
  data={'2026':{'25-170':{'argument_date':'2026-10-05'}}};entry={'term':'2026','docket':'25-170','argument_date':'2026-10-05','video_id':'UZFnuBM0Zjc'}
  self.assertEqual(apply_links(data,{'recordings':{'case':entry}}),1)
  self.assertEqual(apply_links(data,{'recordings':{'case':entry}}),0)
  entry['argument_date']='2026-10-06';entry['video_id']='fH3tO7gyx64'
  self.assertEqual(apply_links(data,{'recordings':{'case':entry}}),0)
 def test_link_row_and_fallback(self):
  url='https://www.youtube.com/watch?v=UZFnuBM0Zjc';description='<p>Title</p><p><a href="https://example.com">Docket</a> &middot; <a href="https://www.oyez.org">oyez.org</a></p><p>Facts</p>'
  result=description_with_video(description,url)
  self.assertIn('oyez.org</a> &middot; <a href="'+url+'">YouTube</a></p><p>Facts',result)
  self.assertEqual(description_with_video(result,url),result)
  self.assertEqual(description_with_video('Facts',url),'Facts<p><a href="'+url+'">YouTube</a></p>')
  self.assertEqual(description_with_video(description,'javascript:bad'),description)
if __name__=='__main__':unittest.main()
