import unittest
import random
from streamanalyser.helpers import exceptions

from streamanalyser.helpers.structures import (
   Intensity,
   Message,
   Author
) 
from streamanalyser.helpers.chatanalyser import (
   ChatAnalyser,
   Fore
)
from streamanalyser.helpers.exceptions import (
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
      self.canalyser = ChatAnalyser(
         generate_random_chat(20, 101, 3)
      )

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
         ConstantsNotAscendingError,
         self.canalyser.init_intensity(
            ['low', 'medium', 'high', 'very high'],
            [0, 1, 0.5, 2.0],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
         )

      with self.assertRaises(ConstantsNotUniqueError):
         ConstantsNotUniqueError,
         self.canalyser.init_intensity(
            ['low', 'medium', 'high', 'very high'],
            [0, 1, 1, 2],
            [Fore.BLUE, Fore.YELLOW, Fore.RED, Fore.MAGENTA],
         )

   def test_calculate_moving_average(self):
      time_frequency = {}
      for i in range(20):
         time_frequency[i]=i+1
         
      result = self.canalyser.calculate_moving_average(
         time_frequency, window=4
      )
      expected = {
         0: 1.0, 1: 1.5, 2: 2.0, 3: 2.5,
         4: 3.5, 5: 4.5, 6: 5.5, 7: 6.5,
         8: 7.5, 9: 8.5, 10: 9.5, 11: 10.5,
         12: 11.5, 13: 12.5, 14: 13.5, 15: 14.5,
         16: 15.5, 17: 16.5, 18: 17.5, 19: 18.5,
      }
      self.assertEqual(result, expected)

      with self.assertRaises(ValueError):
         self.canalyser.calculate_moving_average(
            [], window=1
         )

if __name__ == '__main__':
    unittest.main()
