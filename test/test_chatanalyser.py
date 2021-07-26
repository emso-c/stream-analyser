import unittest
import random
import warnings

from streamanalyser.modules.structures import (
   Intensity,
   Message,
   Author
) 
from streamanalyser.modules.chatanalyser import (
   ChatAnalyser,
   Fore
)
from streamanalyser.modules.exceptions import (
   DifferentListSizeError,
   ConstantsNotAscendingError,
   ConstantsNotUniqueError
)


def generate_random_chat(size, seed, density=0):
   random.seed(seed)
   sample_messages = []
   i = 0
   while i < size:
      if not i == 0 and random.choice(list(range(density))):
         i-=1
      i+=1
      rid = random.random()
      sample_messages.append(Message(
         id=rid,
         text='msg'+str(i),
         time=i,
         author= Author(
            id='u'+str(rid),
            name='usr'+str(i)
         )
      ))
   
   return sample_messages


class TestChatAnalyser(unittest.TestCase):
   def setUp(self):
      warnings.simplefilter('ignore', category=ResourceWarning)
      self.canalyser = ChatAnalyser(
         generate_random_chat(20, 101, 3)
      )
      
      self.canalyser.logger.disabled = True

   def tearDown(self):
      del self.canalyser

   def test_get_frequency(self):
      result = self.canalyser.get_frequency()
      expected = {
         0: 0, 1: 1, 2: 4, 3: 2, 4: 2, 5: 5, 6: 6, 7: 3,
         8: 1, 9: 3, 10: 2,11: 3, 12: 2, 13: 2, 14: 3,
         15: 3,16: 1, 17: 2, 18: 1, 19: 2, 20: 1
      }
      self.assertEqual(result, expected)

   def test_init_intesity(self):
      result = self.canalyser.init_intensity(
         ['low', 'medium', 'high', 'very high'],
         [0, 0.7, 1.2, 2.0],
         [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
      )
      expected = [
         Intensity('low', 0, Fore.BLUE),
         Intensity('medium', 0.7, Fore.YELLOW),
         Intensity('high', 1.2, Fore.RED),
         Intensity('very high', 2.0, Fore.MAGENTA),
      ]
      self.assertEqual(result, expected)
      
      with self.assertRaises(DifferentListSizeError):
         self.canalyser.init_intensity(
            ['low', 'medium', 'high', 'very high'],
            [0, 0.7, 1.2],
            [Fore.BLUE, Fore.YELLOW],
         )

      with self.assertRaises(ConstantsNotAscendingError):
         self.canalyser.init_intensity(
            ['low', 'medium', 'high', 'very high'],
            [0, 1, 0.5, 2.0],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
         )

      with self.assertRaises(ConstantsNotUniqueError):
         self.canalyser.init_intensity(
            ['low', 'medium', 'high', 'very high'],
            [0, 1, 1, 2],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
         )

   def test_calculate_moving_average(self):
      time_frequency = {}
      for i in range(20):
         time_frequency[i]=i+1
      
      self.canalyser.get_frequency()
      self.canalyser.window = 4
      result = self.canalyser.calculate_moving_average()
      expected = {
         0: 0.0, 1: 0.5, 2: 1.6666666666666667,
         3: 1.75, 4: 2.25, 5: 3.25, 6: 3.75,
         7: 4.0, 8: 3.75, 9: 3.25, 10: 2.25,
         11: 2.25, 12: 2.5, 13: 2.25, 14: 2.5,
         15: 2.5, 16: 2.25, 17: 2.25, 18: 1.75,
         19: 1.5, 20: 1.5}

      self.assertEqual(result, expected)

      with self.assertRaises(ValueError):
         ChatAnalyser([], window=1)

   def test_create_highlight_annotation(self):
      self.canalyser.get_frequency()
      self.canalyser.calculate_moving_average()
      self.canalyser.smoothen_mov_avg()
      result = self.canalyser.create_highlight_annotation()
      expected = [
         1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1,
         -1, -1, -1, -1, -1, -1
      ]
      self.assertEqual(result, expected)

   def test_detect_highlight_times(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 4),
         window=5
      )
      self.canalyser.get_frequency()
      self.canalyser.calculate_moving_average()
      self.canalyser.smoothen_mov_avg()
      self.canalyser.create_highlight_annotation()
      highlights = self.canalyser.detect_highlight_times()

      result = ["[{}] ({}->{}): {}".format(
         h.stream_id,
         h.time,
         h.duration,
         h.fdelta
      ) for h in highlights]

      expected = [
         '[undefined] (1->20): 1.7000000000000006',
         '[undefined] (38->10): 0.5050000000000003',
         '[undefined] (54->5): 0.17000000000000082',
         '[undefined] (60->8): 0.5350000000000001'
      ]

      self.assertEqual(result, expected)

   def test_correct_highlights(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5
      )
      self.canalyser.get_frequency()
      self.canalyser.calculate_moving_average()
      self.canalyser.smoothen_mov_avg()
      self.canalyser.create_highlight_annotation()
      self.canalyser.detect_highlight_times()
      
      # manually modified a highlight to be too short
      self.canalyser.highlights[1].duration = 3
      initial_len = len(self.canalyser.highlights)

      corrected_highlights = self.canalyser.correct_highlights()

      result = ["[{}] ({}->{}): {}".format(
         h.stream_id,
         h.time,
         h.duration,
         h.fdelta
      ) for h in corrected_highlights]

      expected = [
         '[undefined] (1->24): 6.148333333333332',
         '[undefined] (38->12): 1.045',
         '[undefined] (73->7): 0.5450000000000017'
      ]

      self.assertEqual(
         len(self.canalyser.highlights), 
         len(corrected_highlights)
      )
      self.assertNotEqual(initial_len, len(corrected_highlights))
      self.assertEqual(result, expected)

   def test_set_highlight_intensities(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5
      )
      self.canalyser.get_frequency()
      self.canalyser.calculate_moving_average()
      self.canalyser.smoothen_mov_avg()
      self.canalyser.create_highlight_annotation()
      self.canalyser.detect_highlight_times()
      self.canalyser.correct_highlights()

      self.canalyser.init_intensity(
         ['low', 'medium', 'high', 'very high'],
         [0, 0.4, 1.1, 1.7],
         [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
      )

      hl_int = self.canalyser.set_highlight_intensities()
      result = [h.colorless_str for h in hl_int]
      expected = [
         '[0:00:01] :  (No messages, very high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] :  (No messages, low intensity, 0.300 diff, 5s duration)',
         '[0:00:38] :  (No messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] :  (No messages, low intensity, 0.545 diff, 7s duration)'
      ]

      self.assertEqual(result, expected)

   def test_get_highlight_messages(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5
      )
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
         '[0:00:01] :  (170 messages, ultra high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] :  (58 messages, medium intensity, 0.300 diff, 5s duration)',
         '[0:00:38] :  (114 messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] :  (75 messages, medium intensity, 0.545 diff, 7s duration)',
      ]

      self.assertEqual(result, expected)

   def test_get_highlight_keywords(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5
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

      highlights = self.canalyser.get_highlight_keywords()

      result = [hl.keywords for hl in highlights]
      expected = [
         ['msg6', 'msg13', 'msg4', 'msg19'],
         ['msg32', 'msg34', 'msg35', 'msg33'],
         ['msg40', 'msg42', 'msg49', 'msg45'],
         ['msg77', 'msg79', 'msg76', 'msg74']
      ]

      self.assertEqual(result, expected)

   def test_guess_context(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5,
         context_path='.\\streamanalyser\\data\\context.json'
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

      self.canalyser.contexts = [
         {
            "reaction_to": "reaction1",
            "triggers": [
               {"phrase": "msg6", "is_exact": False},
               {"phrase": "msg34", "is_exact": False},
               {"phrase": "msg2", "is_exact": False},
            ]
         },
         {
            "reaction_to": "reaction2",
            "triggers": [
               {"phrase": "msg42msg40", "is_exact": True},
               {"phrase": "msg49", "is_exact": True},
            ]
         },
         {
            "reaction_to": "reaction3",
            "triggers": [
               {"phrase": "msg74", "is_exact": False},
               {"phrase": "msg35", "is_exact": False},
            ]
         },
      ]
      expected = [
         ['msg6', 'msg13', 'msg4', 'msg19'],
         ['msg32', 'msg34', 'msg35', 'msg33'],
         ['msg40', 'msg42', 'msg49', 'msg45'],
         ['msg77', 'msg79', 'msg76', 'msg74']
      ]
      
      highlights = self.canalyser.guess_context()
      
      result = [hl.contexts for hl in highlights]

      expected = [
         {'reaction1'},
         {'reaction1', 'reaction3'},
         {'reaction2'},
         {'reaction3'}
      ]

      self.assertEqual(result, expected)

   def test_get_highlights(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5,
         context_path='.\\streamanalyser\\data\\context.json'
      )
      
      self.canalyser.get_frequency()
      self.canalyser.calculate_moving_average()
      self.canalyser.smoothen_mov_avg()
      self.canalyser.create_highlight_annotation()

      self.canalyser.contexts = [
         {
            "reaction_to": "reaction1",
            "triggers": [
               {"phrase": "msg6", "is_exact": False},
               {"phrase": "msg34", "is_exact": False},
               {"phrase": "msg2", "is_exact": False},
            ]
         },
         {
            "reaction_to": "reaction2",
            "triggers": [
               {"phrase": "msg42msg40", "is_exact": True},
               {"phrase": "msg49", "is_exact": True},
            ]
         },
         {
            "reaction_to": "reaction3",
            "triggers": [
               {"phrase": "msg74", "is_exact": False},
               {"phrase": "msg35", "is_exact": False},
            ]
         },
      ]
      highlights = self.canalyser.get_highlights()
      result = [hl.colorless_str for hl in highlights]

      expected = [
         '[0:00:01] reaction1: msg6, msg13, msg4, msg19 (170 messages, ultra high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] reaction3/reaction1: msg32, msg34, msg35, msg33 (58 messages, medium intensity, 0.300 diff, 5s duration)',
         '[0:00:38] reaction2: msg40, msg42, msg49, msg45 (114 messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] reaction3: msg77, msg79, msg76, msg74 (75 messages, medium intensity, 0.545 diff, 7s duration)'
      ]
      # @list_elem_2 reaction1 and reaction3 changes order since there is no order in dictionaries.
      expected2 = [
         '[0:00:01] reaction1: msg6, msg13, msg4, msg19 (170 messages, ultra high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] reaction1/reaction3: msg32, msg34, msg35, msg33 (58 messages, medium intensity, 0.300 diff, 5s duration)',
         '[0:00:38] reaction2: msg40, msg42, msg49, msg45 (114 messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] reaction3: msg77, msg79, msg76, msg74 (75 messages, medium intensity, 0.545 diff, 7s duration)'
      ]
      if result == expected:
         self.assertEqual(result, expected)
      else:
         self.assertEqual(result, expected2)

   def test_analyse(self):
      self.canalyser = ChatAnalyser(
         generate_random_chat(100, 101, 10),
         window=5,
         context_path='.\\streamanalyser\\data\\context.json'
      )
      self.canalyser.contexts = [
         {
            "reaction_to": "reaction1",
            "triggers": [
               {"phrase": "msg6", "is_exact": False},
               {"phrase": "msg34", "is_exact": False},
               {"phrase": "msg2", "is_exact": False},
            ]
         },
         {
            "reaction_to": "reaction2",
            "triggers": [
               {"phrase": "msg42msg40", "is_exact": True},
               {"phrase": "msg49", "is_exact": True},
            ]
         },
         {
            "reaction_to": "reaction3",
            "triggers": [
               {"phrase": "msg74", "is_exact": False},
               {"phrase": "msg35", "is_exact": False},
            ]
         },
      ]

      self.canalyser.analyse()
      result = [hl.colorless_str for hl in self.canalyser.highlights]

      expected = [
         '[0:00:01] reaction1: msg6, msg13, msg4, msg19 (170 messages, ultra high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] reaction3/reaction1: msg32, msg34, msg35, msg33 (58 messages, medium intensity, 0.300 diff, 5s duration)',
         '[0:00:38] reaction2: msg40, msg42, msg49, msg45 (114 messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] reaction3: msg77, msg79, msg76, msg74 (75 messages, medium intensity, 0.545 diff, 7s duration)'
      ]
      # @list_elem_2 reaction1 and reaction3 changes order since there is no order in dictionaries.
      expected2 = [
         '[0:00:01] reaction1: msg6, msg13, msg4, msg19 (170 messages, ultra high intensity, 6.148 diff, 24s duration)',
         '[0:00:31] reaction1/reaction3: msg32, msg34, msg35, msg33 (58 messages, medium intensity, 0.300 diff, 5s duration)',
         '[0:00:38] reaction2: msg40, msg42, msg49, msg45 (114 messages, medium intensity, 1.045 diff, 12s duration)',
         '[0:01:13] reaction3: msg77, msg79, msg76, msg74 (75 messages, medium intensity, 0.545 diff, 7s duration)'
      ]
      if result == expected:
         self.assertEqual(result, expected)
      else:
         self.assertEqual(result, expected2)

if __name__ == '__main__':
    unittest.main()
