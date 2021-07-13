import os
import unittest

from streamanalyser.helpers.loggersetup import create_logger, get_logname

class TestLoggerSetup(unittest.TestCase):
   def test_createlogger(self):

      testlogpath = os.path.join('C:\\Stream Analyser\\Logs', get_logname())
      logger = create_logger(
         __file__,
         fname='test.log',
         sid=None,
         format='%(module)s:%(levelname)s:%(message)s',
         mode='w'
      )
      self.assertTrue(os.path.exists(testlogpath))

      logger.info('test')
      logger.debug('test')
      logger.warning('test')
      logger.error('test')
      logger.critical('test')
      lvs = ['INFO','DEBUG','WARNING','ERROR','CRITICAL']
      with open(testlogpath, 'r') as f:
         for i, line in enumerate(f.readlines()):
            self.assertEqual(line, f'test_loggersetup:{lvs[i]}:test\n')


if __name__ == '__main__':
   unittest.main()