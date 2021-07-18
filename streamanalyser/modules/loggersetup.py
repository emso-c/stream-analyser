import logging
import os
from datetime import datetime

from .filehandler import streamanalyser_filehandler as sf

def create_logger(name, fname=None, sid=None, format=None, mode='a', def_level=logging.ERROR, level=logging.DEBUG):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not format:
        if sid:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:[{sid}]:%(message)s'
        else:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s'
    
    if not os.path.exists(sf.log_path):
        os.makedirs(sf.log_path)
   
    if not fname:
        fname = get_logname()

    logging.basicConfig(
        level=def_level,
        format=format,
        filename=os.path.join(sf.log_path, fname),
        encoding='utf-8',
        filemode=mode
    )
    console = logging.StreamHandler()
    console.setLevel(def_level)
    console.setFormatter(logging.Formatter(format))
    logging.getLogger(name).addHandler(console)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger

def get_logname() -> str:
    """ Gets log name in Y-M-Wn format where n is week number, starts from 0
        Example: 2021-06-W0 """
    weekno = datetime.today().isocalendar()[1] - datetime.today().replace(day=1).isocalendar()[1]
    return datetime.today().strftime('%Y-%m-W')+str(weekno)+".log"