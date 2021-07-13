import unittest

from streamanalyser.helpers.datarefiner import DataRefiner
from streamanalyser.helpers.structures import Message, Author

class test(unittest.TestCase):
    def test_refine_raw_messages(self):

        sample_raw_messages = []
        for i in range(6):
            sample_raw_messages.append({
                'message_id': i,
                'message': 'msg'+str(i),
                'time_in_seconds': i,
                'author': {
                    'id': i,
                    'name': 'name'+str(i)
                }
            })
        expected_messages = []
        for i in range(6):
            expected_messages.append(
                Message(
                    id=i,
                    text='msg'+str(i),
                    time=i,
                    author=Author(
                        id=i,
                        name='name'+str(i),
                    )
                )
            )

        # w/out limit
        result_messages = self.refiner.refine_raw_messages(
            sample_raw_messages,
            msglimit=None
        )
        self.assertEqual(
            result_messages,
            expected_messages
        )

        # w/ limit
        result_messages = self.refiner.refine_raw_messages(
            sample_raw_messages,
            msglimit=3
        )
        self.assertEqual(
            result_messages,
            expected_messages[:3]
        )

        # skip corrupt
        result_messages = self.refiner.refine_raw_messages(
            [{'corrupt_data':'test'}],
        )
        self.assertEqual(
            result_messages,
            []
        )
        
    def setUp(self):
        self.refiner = DataRefiner()

    def tearDown(self):
        del self.refiner

if __name__ == '__main__':
    unittest.main()
