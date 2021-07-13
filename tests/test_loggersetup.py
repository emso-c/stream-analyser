import os
import unittest

from streamanalyser.helpers.filehandler import streamanalyser_filehandler as sf
from streamanalyser.helpers.loggersetup import create_logger


class TestLoggerSetup(unittest.TestCase):
   def test_createlogger(self):
      testlogpath = os.path.join(sf.log_path, 'test.log')
      logger = create_logger(
         'test.log',
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