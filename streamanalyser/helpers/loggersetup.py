import logging
import os

from .filehandler import streamanalyser_filehandler as sf


def create_logger(name, sid=None, format=None, mode='a', def_level=logging.ERROR, level=logging.DEBUG):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not format:
        if sid:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:[{sid}]:%(message)s'
        else:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s'
    
    try:
        if not os.path.exists(sf.log_path):
            os.makedirs(sf.log_path)
    except:
        raise PermissionError(f"Permission denied")

    logging.basicConfig(
        level=def_level,
        format=format,
        filename=os.path.join(sf.log_path, name),
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