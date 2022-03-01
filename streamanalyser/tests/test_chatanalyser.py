import json
import os
import unittest
import random
import warnings

from modules.chatanalyser import ChatAnalyser, Fore
from modules.structures import (
    Intensity,
    Message,
    Author,
    Context,
    Trigger
)
from modules.exceptions import (
    DifferentListSizeError,
    ConstantsNotAscendingError,
    ConstantsNotUniqueError,
    DuplicateContextException,
    UnexpectedException,
    ContextsAllCorruptException,
    PathAlreadyExistsException
)


def generate_random_chat(size, seed, density=0):
    random.seed(seed)
    sample_messages = []
    i = 0
    while i < size:
        if not i == 0 and random.choice(list(range(density))):
            i -= 1
        i += 1
        rid = random.random()
        sample_messages.append(
            Message(
                id=rid,
                text="msg" + str(i),
                time=i,
                author=Author(id="u" + str(rid), name="usr" + str(i)),
            )
        )

    return sample_messages

SAMPLE_CONTEXT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "contexts.json"
)
ANOTHER_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "another_context.json"
)
PARTIAL_CORRUPT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "partial_corrupt_context.json"
)
FULL_CORRUPT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "full_corrupt_context.json"
)

sample_contexts = [
            {
                "reaction_to": "reaction1",
                "triggers": [
                    {"phrase": "msg6", "is_exact": False},
                    {"phrase": "msg34", "is_exact": False},
                    {"phrase": "msg2", "is_exact": False},
                    {"phrase": "msg32", "is_exact": False},
                ],
            },
            {
                "reaction_to": "reaction2",
                "triggers": [
                    {"phrase": "msg42msg40", "is_exact": True},
                    {"phrase": "msg49", "is_exact": True},
                    {"phrase": "msg40", "is_exact": True},
                ],
            },
            {
                "reaction_to": "reaction3",
                "triggers": [
                    {"phrase": "msg74", "is_exact": False},
                    {"phrase": "msg35", "is_exact": False},
                    {"phrase": "msg77", "is_exact": False},
                ],
            },
        ]

partially_corrupt_contexts = [
    {"wrong_key": "reaction"},
    {
        "reaction_to": "reaction3",
        "triggers": [
            {"phrase": "msg35", "is_exact": False},
        ],
    },
]

fully_corrupt_contexts = [
    {"wrong_key": "reaction"},
    {"wrong_key2": "reaction"},
]


class TestChatAnalyser(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", category=ResourceWarning)

        with open(SAMPLE_CONTEXT_PATH, "w") as file:
            file.write(json.dumps(sample_contexts))
        with open(ANOTHER_PATH, "w") as file:
            file.write(json.dumps(sample_contexts))
        with open(PARTIAL_CORRUPT_PATH, "w") as file:
            file.write(json.dumps(partially_corrupt_contexts))
        with open(FULL_CORRUPT_PATH, "w") as file:
            file.write(json.dumps(fully_corrupt_contexts))
        self.canalyser = ChatAnalyser(
            generate_random_chat(20, 101, 3),
            log_path=None,
            default_context_path=None
        )
        self.canalyser.logger.disabled = True

    def tearDown(self):
        os.remove(SAMPLE_CONTEXT_PATH)
        os.remove(ANOTHER_PATH)
        os.remove(PARTIAL_CORRUPT_PATH)
        os.remove(FULL_CORRUPT_PATH)
        del self.canalyser

    def test_get_frequency(self):
        result = self.canalyser.get_frequency()
        expected = {
            0: 0,
            1: 1,
            2: 4,
            3: 2,
            4: 2,
            5: 5,
            6: 6,
            7: 3,
            8: 1,
            9: 3,
            10: 2,
            11: 3,
            12: 2,
            13: 2,
            14: 3,
            15: 3,
            16: 1,
            17: 2,
            18: 1,
            19: 2,
            20: 1,
        }
        self.assertEqual(result, expected)

    def test_init_intesity(self):
        result = self.canalyser.init_intensity(
            ["low", "medium", "high", "very high"],
            [0, 0.7, 1.2, 2.0],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
        )
        expected = [
            Intensity("low", 0, Fore.BLUE),
            Intensity("medium", 0.7, Fore.YELLOW),
            Intensity("high", 1.2, Fore.RED),
            Intensity("very high", 2.0, Fore.MAGENTA),
        ]
        self.assertEqual(result, expected)

        with self.assertRaises(DifferentListSizeError):
            self.canalyser.init_intensity(
                ["low", "medium", "high", "very high"],
                [0, 0.7, 1.2],
                [Fore.BLUE, Fore.YELLOW],
            )

        with self.assertRaises(ConstantsNotAscendingError):
            self.canalyser.init_intensity(
                ["low", "medium", "high", "very high"],
                [0, 1, 0.5, 2.0],
                [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
            )

        with self.assertRaises(ConstantsNotUniqueError):
            self.canalyser.init_intensity(
                ["low", "medium", "high", "very high"],
                [0, 1, 1, 2],
                [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
            )

    def test_calculate_moving_average(self):
        time_frequency = {}
        for i in range(20):
            time_frequency[i] = i + 1

        self.canalyser.get_frequency()
        self.canalyser.window = 4
        result = self.canalyser.calculate_moving_average()
        expected = {
            0: 0.0,
            1: 0.5,
            2: 1.6666666666666667,
            3: 1.75,
            4: 2.25,
            5: 3.25,
            6: 3.75,
            7: 4.0,
            8: 3.75,
            9: 3.25,
            10: 2.25,
            11: 2.25,
            12: 2.5,
            13: 2.25,
            14: 2.5,
            15: 2.5,
            16: 2.25,
            17: 2.25,
            18: 1.75,
            19: 1.5,
            20: 1.5,
        }

        self.assertEqual(result, expected)

        with self.assertRaises(ValueError):
            ChatAnalyser([], log_path=None, window=1, default_context_path=None)

    def test_create_highlight_annotation(self):
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        result = self.canalyser.create_highlight_annotation()
        expected = [
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
        ]
        self.assertEqual(result, expected)

    def test_detect_highlight_times(self):
        self.canalyser = ChatAnalyser(generate_random_chat(100, 101, 4), log_path=None, window=5, default_context_path=None)
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        highlights = self.canalyser.detect_highlight_times()

        result = [
            "[{}] ({}->{}): {}".format(h.stream_id, h.time, h.duration, h.fdelta)
            for h in highlights
        ]
        expected = [
            '[undefined] (1->20): 1.7000000000000006',
            '[undefined] (38->10): 0.5050000000000003', 
            '[undefined] (54->5): 0.17000000000000082',
            '[undefined] (60->8): 0.5350000000000001'
        ]

        self.assertEqual(result, expected)

    def test_correct_highlights(self):
        self.canalyser = ChatAnalyser(generate_random_chat(100, 101, 10), log_path=None, window=5, default_context_path=None)
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.detect_highlight_times()

        # manually modified a highlight to be too short
        self.canalyser.highlights[1].duration = 3
        initial_len = len(self.canalyser.highlights)

        corrected_highlights = self.canalyser.correct_highlights()

        result = [
            "[{}] ({}->{}): {}".format(h.stream_id, h.time, h.duration, h.fdelta)
            for h in corrected_highlights
        ]

        expected = [
            '[undefined] (31->3): 0.30000000000000426',
            '[undefined] (38->12): 1.045',
            '[undefined] (73->7): 0.5450000000000017'
        ]

        self.assertEqual(len(self.canalyser.highlights), len(corrected_highlights))
        self.assertNotEqual(initial_len, len(corrected_highlights))
        self.assertEqual(result, expected)

    def test_set_highlight_intensities(self):
        self.canalyser = ChatAnalyser(generate_random_chat(100, 101, 10), log_path=None, window=5, default_context_path=None)
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.detect_highlight_times()
        self.canalyser.correct_highlights()

        self.canalyser.init_intensity(
            ["low", "medium", "high", "very high"],
            [0, 0.4, 1.1, 1.7],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
        )

        hl_int = self.canalyser.set_highlight_intensities()
        result = [h.colorless_str for h in hl_int]

        expected = [
            '[0:00:31] :  (No messages, medium intensity, 0.300 diff, 5s duration)',
            '[0:00:38] :  (No messages, high intensity, 1.045 diff, 12s duration)',
            '[0:01:13] :  (No messages, medium intensity, 0.545 diff, 7s duration)'
        ]

        self.assertEqual(result, expected)

    def test_get_highlight_messages(self):
        self.canalyser = ChatAnalyser(generate_random_chat(100, 101, 10), log_path=None, window=5, default_context_path=None)
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.detect_highlight_times()
        self.canalyser.correct_highlights()
        self.canalyser.init_intensity()
        self.canalyser.set_highlight_intensities()

        highlights = self.canalyser.get_highlight_messages()

        result = [hl.colorless_str for hl in highlights]

        expected = [
            '[0:00:31] :  (58 messages, medium intensity, 0.300 diff, 5s duration)',
            '[0:00:38] :  (114 messages, very high intensity, 1.045 diff, 12s duration)',
            '[0:01:13] :  (75 messages, high intensity, 0.545 diff, 7s duration)'
        ]

        self.assertEqual(result, expected)

    def test_get_highlight_keywords(self):
        self.canalyser = ChatAnalyser(generate_random_chat(100, 101, 10), log_path=None, window=5, default_context_path=None)
        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.detect_highlight_times()
        self.canalyser.correct_highlights()
        self.canalyser.init_intensity()
        self.canalyser.set_highlight_intensities()
        self.canalyser.get_highlight_messages()

        highlights = self.canalyser.get_highlight_keywords()

        result = [hl.keywords for hl in highlights]
        expected = [
            ['msg32', 'msg34', 'msg35', 'msg33'],
            ['msg40', 'msg42', 'msg49', 'msg45'],
            ['msg77', 'msg79', 'msg76', 'msg74']
        ]
        
        self.assertEqual(result, expected)

    def test_guess_context(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            window=5,
            default_context_path=SAMPLE_CONTEXT_PATH,
        )

        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.detect_highlight_times()
        self.canalyser.correct_highlights()
        self.canalyser.init_intensity()
        self.canalyser.set_highlight_intensities()
        self.canalyser.get_highlight_messages()
        self.canalyser.get_highlight_keywords()

        expected = [
            ["msg6", "msg13", "msg4", "msg19"],
            ["msg32", "msg34", "msg35", "msg33"],
            ["msg40", "msg42", "msg49", "msg45"],
            ["msg77", "msg79", "msg76", "msg74"],
        ]
        self.canalyser.get_contexts()
        highlights = self.canalyser.guess_context()
        result = [hl.contexts for hl in highlights]
        expected = [
            {"reaction3", "reaction1"},
            {"reaction2"},
            {"reaction3"},
        ]
        expected2 = [
            {"reaction1", "reaction3"},
            {"reaction2"},
            {"reaction3"},
        ]
        try:
            self.assertEqual(result, expected)
        except:
            self.assertEqual(result, expected2)

    def test_get_highlights(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            window=5,
            default_context_path=SAMPLE_CONTEXT_PATH,
        )

        self.canalyser.get_frequency()
        self.canalyser.calculate_moving_average()
        self.canalyser.smoothen_mov_avg()
        self.canalyser.create_highlight_annotation()
        self.canalyser.get_contexts()
        highlights = self.canalyser.get_highlights()
        result = [hl.colorless_str for hl in highlights]

        expected = [
            '[0:00:31] reaction1: msg32 (58 messages, medium intensity, 0.300 diff, 5s duration)',
            '[0:00:38] reaction2: msg40 (114 messages, very high intensity, 1.045 diff, 12s duration)',
            '[0:01:13] reaction3: msg77 (75 messages, high intensity, 0.545 diff, 7s duration)'
        ]
        self.assertEqual(result, expected)

    def test_analyse(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            window=5,
            default_context_path=SAMPLE_CONTEXT_PATH,
        )
        
        self.canalyser.analyse()
        result = [hl.colorless_str for hl in self.canalyser.highlights]
        expected = [
            "[0:00:31] reaction1: msg32 (58 messages, medium intensity, 0.300 diff, 5s duration)",
            "[0:00:38] reaction2: msg40 (114 messages, very high intensity, 1.045 diff, 12s duration)",
            "[0:01:13] reaction3: msg77 (75 messages, high intensity, 0.545 diff, 7s duration)",
        ]
        self.assertEqual(result, expected)

    def test_context_source_structure(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            default_context_path=None,
        )

        # RESET
        self.canalyser.source.reset()
        self.assertEqual(self.canalyser.source.paths, [])


        # ADD
        ## basic
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.add(ANOTHER_PATH)
        self.assertEqual(
            self.canalyser.source.paths,
            [SAMPLE_CONTEXT_PATH, ANOTHER_PATH]
        )
        self.canalyser.source.reset()

        ## should raise PathAlreadyExistsException if path already exists
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        with self.assertRaises(PathAlreadyExistsException):
            self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.reset()
        
        ## should raise PathAlreadyExistsException if path is None or empty
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        with self.assertRaises(ValueError):
            self.canalyser.source.add(None)
            self.canalyser.source.add("")
        self.canalyser.source.reset()


        # REMOVE
        ## by path
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.remove(byPath=SAMPLE_CONTEXT_PATH)
        self.assertEqual(self.canalyser.source.paths, [])
        self.canalyser.source.reset()

        ## by index
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.remove(byIndex=0)
        self.assertEqual(self.canalyser.source.paths, [])
        self.canalyser.source.reset()

        ## remove last with index
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.remove(byIndex=-1)
        self.assertEqual(self.canalyser.source.paths, [])
        self.canalyser.source.reset()

        # should raise value error when both parameters are used
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        with self.assertRaises(ValueError):
            self.canalyser.source.remove(
                byPath=SAMPLE_CONTEXT_PATH,
                byIndex=0
            )
        self.canalyser.source.reset()

        # should raise value error when none of the parameters are used
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        with self.assertRaises(ValueError):
            self.canalyser.source.remove()
        self.canalyser.source.reset()


        # UPDATE
        ## basic
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.source.update(SAMPLE_CONTEXT_PATH, ANOTHER_PATH)
        self.assertEqual(self.canalyser.source.paths, [ANOTHER_PATH])
        self.canalyser.source.reset()


    def test_read_contexts_from_sources(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            default_context_path=SAMPLE_CONTEXT_PATH,
        )

        # basic
        self.canalyser.read_contexts_from_sources()
        self.assertTrue(self.canalyser.contexts, sample_contexts)

        # should reset contexts each time
        self.canalyser.read_contexts_from_sources()
        self.canalyser.read_contexts_from_sources()
        self.assertTrue(self.canalyser.contexts, sample_contexts)

    def test__check_contexts(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            default_context_path=None,
        )

        # should not do anything
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.read_contexts_from_sources()
        self.canalyser._check_contexts()
        self.assertEqual(self.canalyser.contexts, sample_contexts)

        # should raise exception if duplicate context is found
        self.canalyser.source.add(ANOTHER_PATH)
        self.canalyser.read_contexts_from_sources()
        with self.assertRaises(DuplicateContextException):
            self.canalyser._check_contexts()

        # should merge duplicate contexts on `autofix = True`
        # instead of throwing error
        self.canalyser._check_contexts(autofix=True)
        
        self.assertEqual(
            self.canalyser.contexts,
            [{'reaction_to': 'reaction1', 'triggers': [{'phrase': 'msg6', 'is_exact': False}, {'phrase': 'msg34', 'is_exact': False}, {'phrase': 'msg2', 'is_exact': False}, {'phrase': 'msg32', 'is_exact': False}, {'phrase': 'msg6', 'is_exact': False}, {'phrase': 'msg34', 'is_exact': False}, {'phrase': 'msg2', 'is_exact': False}, {'phrase': 'msg32', 'is_exact': False}]}, {'reaction_to': 'reaction2', 'triggers': [{'phrase': 'msg42msg40', 'is_exact': True}, {'phrase': 'msg49', 'is_exact': True}, {'phrase': 'msg40', 'is_exact': True}, {'phrase': 'msg42msg40', 'is_exact': True}, {'phrase': 'msg49', 'is_exact': True}, {'phrase': 'msg40', 'is_exact': True}]}, {'reaction_to': 'reaction3', 'triggers': [{'phrase': 'msg74', 'is_exact': False}, {'phrase': 'msg35', 'is_exact': False}, {'phrase': 'msg77', 'is_exact': False}, {'phrase': 'msg74', 'is_exact': False}, {'phrase': 'msg35', 'is_exact': False}, {'phrase': 'msg77', 'is_exact': False}]}]
        )

    def test_parse_contexts(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            default_context_path=None,
        )
        self.canalyser.source.add(SAMPLE_CONTEXT_PATH)
        self.canalyser.read_contexts_from_sources()
        contexts = self.canalyser.parse_contexts()
        self.assertEqual(type(contexts[0]), Context)
        self.assertEqual(type(contexts[0].triggers[0]), Trigger)


        self.canalyser.source.update(SAMPLE_CONTEXT_PATH, PARTIAL_CORRUPT_PATH)
        self.canalyser.read_contexts_from_sources()

        # should raise exception when parsing corrupt data
        with self.assertRaises(Exception):
            self.canalyser.parse_contexts()

        # should skip corrupt data if autofix is enabled
        contexts = self.canalyser.parse_contexts(autofix=True)
        self.assertEqual(contexts[0].reaction_to, partially_corrupt_contexts[1]["reaction_to"])

        self.canalyser.source.update(PARTIAL_CORRUPT_PATH, FULL_CORRUPT_PATH)
        self.canalyser.read_contexts_from_sources()
        # should raise ContextsAllCorruptException if autofix is true and all the data is corrupt
        with self.assertRaises(ContextsAllCorruptException):
            self.canalyser.parse_contexts(autofix=True)
        
        # should raise another Exception depending on the source file content
        # if autofix is false and all the data is corrupt
        with self.assertRaises(Exception):
            self.canalyser.parse_contexts(autofix=False)

    def test_get_contexts(self):
        self.canalyser = ChatAnalyser(
            generate_random_chat(100, 101, 10),
            log_path=None,
            default_context_path=SAMPLE_CONTEXT_PATH,
        )

        # should return all parsed sample contexts
        self.canalyser.get_contexts()
        self.assertEqual(
            [context.reaction_to for context in self.canalyser.contexts],
            [context['reaction_to'] for context in sample_contexts],
        )


        self.canalyser.source.reset()
        self.canalyser.source.add(PARTIAL_CORRUPT_PATH)
        
        # should throw error if anything is wrong when autofix is disabled
        with self.assertRaises(KeyError):
            self.canalyser.get_contexts(autofix=False)
        
        # should return some parsed contexts when autofix is enabled
        self.canalyser.get_contexts(autofix=True)
        self.assertEqual(
            [context.reaction_to for context in self.canalyser.contexts],
            [context['reaction_to'] for context in partially_corrupt_contexts[1:]],
        )


        self.canalyser.source.reset()
        self.canalyser.source.add(FULL_CORRUPT_PATH)
        
        # should return nothing if all the data is corrupt when autofix is enabled
        self.canalyser.get_contexts(autofix=True)
        self.assertTrue(len(self.canalyser.contexts)==0)
        
        # should throw error if all the data is corrupt when autofix is disabled
        with self.assertRaises(KeyError):
            self.canalyser.get_contexts(autofix=False)
        
if __name__ == "__main__":
    unittest.main()
