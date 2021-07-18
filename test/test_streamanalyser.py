import unittest
import warnings
import os
import shutil

from streamanalyser import streamanalyser as sa 


class TestStreamAnalyser(unittest.TestCase):
   def setUp(self):
      warnings.simplefilter('ignore', category=ResourceWarning)

   def test_collect_data(self):
      with sa.StreamAnalyser('um196SMIoR8', 1) as analyser:
         analyser.logger.disabled = True
         analyser.collector.logger.disabled = True
         analyser.filehandler.logger.disabled = True
         
         analyser._collect_data()
         raw_messages = analyser._raw_messages
         expected = [{
            'message_id':  'CjkKGkNMSHU0ZmpxNl9FQ0ZjTWZmUW9kWlJzSXFBEht'+
                           'DSlRCd0szbTZfRUNGY2ZGeEFvZHVVUUEwZzA%3D',
            'message': 'kon...',
            'time_in_seconds': 0,
            'author': {
               'name': 'RathalosRE',
               'id': 'UCX07ffYvacTkgo89MjNpweg'
         }}]
         self.assertEqual(raw_messages, expected)

         metadata = analyser.metadata
         expected = {
            'author_name': 'Towa Ch. 常闇トワ',
            'author_url': 'https://www.youtube.com/channel/UC1uv2Oq6kNxgATlCiez59hw',
            'height': 113,
            'html': '<iframe width="200" height="113" '
                     'src="https://www.youtube.com/embed/um196SMIoR8?feature=oembed" '
                     'frameborder="0" allow="accelerometer; autoplay; clipboard-write; '
                     'encrypted-media; gyroscope; picture-in-picture" '
                     'allowfullscreen></iframe>',
            'provider_name': 'YouTube',
            'provider_url': 'https://www.youtube.com/',
            'thumbnail_height': 360,
            'thumbnail_url': 'https://i.ytimg.com/vi/um196SMIoR8/hqdefault.jpg',
            'thumbnail_width': 480,
            'title': '【APEX】英語…頑張ります！！\u3000w/ Roboco,Amelia【常闇トワ/ホロライブ】',
            'type': 'video',
            'version': '1.0',
            'width': 200}
         self.assertEqual(metadata, expected)

   def test_cache_messages(self):
      with sa.StreamAnalyser('testid', 1) as analyser:
         analyser.logger.disabled = True
         analyser.filehandler.logger.disabled = True

         analyser._raw_messages = [{'test':'test'}]
         analyser._cache_messages()

         self.assertTrue(os.path.isfile(
            os.path.join(
               analyser.filehandler.sid_path,
               analyser.filehandler.message_fname
         )))

         # clear files
         shutil.rmtree(analyser.filehandler.sid_path)
   
   def test_cache_metadata(self):
      with sa.StreamAnalyser('testid', 1) as analyser:
         analyser.logger.disabled = True
         analyser.filehandler.logger.disabled = True

         analyser.metadata = {'test':'test','test2':{'test3':'test3'}}
         analyser._cache_metadata()

         self.assertTrue(os.path.isfile(
            os.path.join(
               analyser.filehandler.sid_path,
               analyser.filehandler.metadata_fname
         )))

         # clear files
         shutil.rmtree(analyser.filehandler.sid_path)


if __name__ == '__main__':
    unittest.main()
