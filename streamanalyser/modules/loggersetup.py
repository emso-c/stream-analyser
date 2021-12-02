import logging
import os
from datetime import datetime

def create_logger(
    name,
    folder_path,
    file_name=None,
    sid='Undefined',
    format=None,
    mode="a",
    def_level=logging.ERROR,
    level=logging.DEBUG,
):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    format = format or f"%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:{f'[{sid}]:' if sid else ''}%(message)s"
    file_name = file_name or get_logname()

    if folder_path:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        logging.basicConfig(
            level=def_level,
            filename=os.path.join(folder_path, file_name),
            format=format,
            encoding="utf-8",
            filemode=mode,
        )
    else:
        # not create a log file
        logging.basicConfig(
            level=def_level,
            format=format,
            encoding="utf-8",
        )
    console = logging.StreamHandler()
    console.setLevel(def_level)
    console.setFormatter(logging.Formatter(format))
    logging.getLogger(name).addHandler(console)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


def get_logname() -> str:
    """Gets log name in Y-M-Wn format where n is week number, starts from 0
    Example: 2021-06-W0"""
    weekno = (
        datetime.today().isocalendar()[1]
        - datetime.today().replace(day=1).isocalendar()[1]
    )
    return datetime.today().strftime("%Y-%m-W") + str(weekno) + ".log"
