import unittest
import warnings

from modules.datarefiner import DataRefiner
from modules.structures import Icon, Message, Author


class TestDataRefiner(unittest.TestCase):
    def test_refine_raw_messages(self):
        # w/out limit
        result_messages = self.refiner.refine_raw_messages(
            self.sample_raw_messages, msglimit=None
        )
        self.assertEqual(result_messages, self.expected_messages)

        # w/ limit
        result_messages = self.refiner.refine_raw_messages(
            self.sample_raw_messages, msglimit=3
        )
        self.assertEqual(result_messages, self.expected_messages[:3])

        result_messages = self.refiner.refine_raw_messages(
            [{"corrupt_data": "test"}],
        )
        self.assertEqual(result_messages, [])

    def test_get_authors(self):
        result_authors = self.refiner.get_authors()
        self.assertEqual(result_authors, [])

        self.refiner.refine_raw_messages(self.sample_raw_messages)
        result_authors = self.refiner.get_authors()
        self.assertEqual(result_authors, self.expected_authors)

    def setUp(self):
        warnings.simplefilter("ignore", category=ResourceWarning)
        self.refiner = DataRefiner(log_path=None)
        self.refiner.logger.disabled = True

        self.sample_raw_messages, self.expected_messages, self.expected_authors = [], [], []
        for i in range(6):
            self.sample_raw_messages.append({
                    "message_id": str(i),
                    "message_type": "text_message",
                    "message": "msg" + str(i),
                    "time_in_seconds": i,
                    "author": {
                        "id": str(i),
                        "name": "name" + str(i),
                        "images": [{
                            "id": str(i),
                            "url": "url" + str(i), 
                        }],
                    },
                }
            )

            author = Author(
                id=str(i),
                name="name"+str(i),
                images={
                    "profile": [Icon(id=str(i), url="url"+str(i))],
                    "membership": []
                },
            )
            self.expected_authors.append(author)
            self.expected_messages.append(
                Message(
                    id=str(i),
                    text="msg"+str(i),
                    time=i,
                    author=author
                )
            )
    def tearDown(self):
        del self.refiner


if __name__ == "__main__":
    unittest.main()
