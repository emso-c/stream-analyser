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
      
if __name__ == '__main__':
    unittest.main()
