import logging
import os
import unittest

from modules.loggersetup import create_logger



class TestLoggerSetup(unittest.TestCase):
    def test_createlogger(self):
        logger = create_logger(
            __file__,
            folder_path="C:\\Stream Analyser\\Logs",
            file_name="_test.log",
            sid=None,
            format="%(module)s:%(levelname)s:%(message)s",
            mode="w",
        )
        self.assertTrue(os.path.exists(self.test_log_path))

        logger.info("test")
        logger.debug("test")
        logger.warning("test")
        # logger.error('test')
        # logger.critical('test')
        lvls = ["INFO", "DEBUG", "WARNING"]  #'ERROR','CRITICAL']
        with open(self.test_log_path, "r") as f:
            for i, line in enumerate(f.readlines()):
                self.assertEqual(line, f"test_loggersetup:{lvls[i]}:test\n")
    def setUp(self):
        self.test_log_path = "C:\\Stream Analyser\\Logs\\_test.log"
    def tearDown(self):
        logging.shutdown()
        os.remove(self.test_log_path)


if __name__ == "__main__":
    unittest.main()
