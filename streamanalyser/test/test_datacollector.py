import unittest
import warnings

from modules.datacollector import DataCollector


# TODO Fix:
# On: Chatdownloader call with limit
# Warning: unclosed <ssl.SSLSocket> on break


class TestDataCollector(unittest.TestCase):
    def test_collect_metadata(self):
        metadata = self.collector.collect_metadata()
        self.assertEqual(
            metadata["title"], "4 A.M Study Session 📚 - [lofi hip hop/chill beats]"
        )

    def test_fetch_raw_messages(self):
        raw_messages = self.collector.fetch_raw_messages()
        self.assertEqual(
            raw_messages[0]["message_id"],
            "CkUKGkNOU255NHJNblBBQ0ZSaXN3UW9kQkdjQWVBEidDT1My"
            + "dV92TG5QQUNGY3RsbXdvZDVaZ01RUTE2MTk0NjM2MTQzNTE%3D",
        )

        # messages fetched with a limit
        # should be considered incomplete
        self.assertFalse(self.collector.iscomplete)

    def test_fetch_missing_messages(self):
        raw_messages = self.collector.fetch_missing_messages(20, 10, 2)

        self.assertEqual(raw_messages[0]["author"]["id"], "UCjbWfSrdmmtdRSRYcoqjc-Q")

        # messages fetched with a limit
        # should be considered incomplete
        self.assertFalse(self.collector.iscomplete)

    def setUp(self):
        warnings.simplefilter("ignore", category=ResourceWarning)
        self.example_url = "TURbeWK2wwg"
        self.collector = DataCollector(self.example_url, msglimit=1, log_path=None)
        self.collector.logger.disabled = True

    def tearDown(self):
        del self.collector


if __name__ == "__main__":
    unittest.main()
