import unittest
import pprint
from streamanalyser.helpers.datacollector import DataCollector


#TODO Fix:
# On: Chatdownloader call with limit
# Warning: unclosed <ssl.SSLSocket> on break
class TestDataCollector(unittest.TestCase):
   def test_collect_metadata(self):
      metadata = self._collector.collect_metadata()
      self.assertEqual(
         metadata['title'],
         '4 A.M Study Session 📚 - [lofi hip hop/chill beats]'
      )

   def test_fetch_raw_messages(self):
      raw_messages = self._collector.fetch_raw_messages()
      self.assertEqual(
         raw_messages[0]['message_id'],
         'CkUKGkNOU255NHJNblBBQ0ZSaXN3UW9kQkdjQWVBEidDT1My' +
         'dV92TG5QQUNGY3RsbXdvZDVaZ01RUTE2MTk0NjM2MTQzNTE%3D'
      )

      # messages fetched with a limit should be considered incomplete
      self.assertFalse(self._collector.iscomplete)


   def setUp(self):
      self.example_url = 'TURbeWK2wwg'
      self._collector = DataCollector(
         self.example_url,
         msglimit=1
      )
      self._collector.handlers = []

   def tearDown(self):
      del self._collector


if __name__ == '__main__':
   unittest.main()