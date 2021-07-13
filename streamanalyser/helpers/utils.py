import os
import gzip
from shutil import copyfileobj
from datetime import datetime
from time import time

import loggersetup


def get_logname() -> str:
    """ Gets log name in Y-M-Wn format where n is week number, starts from 0
        Example: 2021-06-W0 """
    weekno = datetime.today().isocalendar()[1] - datetime.today().replace(day=1).isocalendar()[1]
    return datetime.today().strftime('%Y-%m-W')+str(weekno)+".log"

_package_path = os.path.abspath(__file__).split('utils\\utils.py')[0]
logger = loggersetup.create_logger(
    name=__file__,
    logpath=_package_path+'\\src\\logs\\'+get_logname()
)

percentage = lambda current, out_of: round(int(current*100/out_of))

def delete_file(path):
    try:
        os.remove(path)
        logger.info(f'{path} removed')
    except FileNotFoundError:
        logger.debug(f"{path} couldn't be found")
    except Exception as e:
        logger.error(f"cound't remove {path}")


def compress_file(path):
        try:
            with open(path, 'rb') as f_in:
                with gzip.open(path+".gz", 'wb') as f_out:
                    copyfileobj(f_in, f_out)
            os.remove(path)
        except Exception as e:
            logger.critical(e)
            raise Exception(e)
        logger.info('File compressed')


def decompress_file(path):
    try:
        with gzip.open(path+'.gz', 'rb') as f_in:
            with open(path, 'wb') as f_out:
                copyfileobj(f_in, f_out)
        os.remove(path+'.gz')
    except Exception as e:
        logger.critical(e)
        raise Exception(e)
    logger.info('File decompressed')


def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            logger.debug(f"{path} created")
        except PermissionError as e:
            print(f"{e}\nTry another path or re-run the program in administrator mode.")
            logger.error(f"Permission denied to {path}")

def delete_file_if_exists(path):
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.debug(f"{path} deleted")
        except Exception as e:
            logger.error(f"Couldn't delete file: {e}")  


def normalize(text) -> str:
    """ Normalizes string by removing punctuations, trimming and lowering.
        If a string only consists of punctuations, the text is trimmed only. """

    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""" # maybe add ？！ー～…
    if all(ch in punctuation for ch in text):
        return text.strip()
    return text.lower().strip().translate(str.maketrans('', '', punctuation))


def creation_time_in_days(file_path) -> int:
    """ Returns difference between the creation time and
        the current time of the file in days """

    if os.path.isfile(file_path):
        ctime = os.path.getctime(file_path)
        return int(datetime.fromtimestamp(int(time()-ctime)).strftime('%d'))
    logger.debug(f"{file_path} is not a file")
    return 0

def delete_old_files(folder_path, time_limit_in_days):
    """ Delete files in a folder older than the time limit. """

    for name in os.listdir(folder_path):
        fpath = os.path.join(folder_path, name)
        if creation_time_in_days(fpath) >= time_limit_in_days:
            delete_file(fpath)

def filenames(path) -> list[str]:
    """ Returns file names in a path without extension """

    logger.info(f"Finding file names in {path}")
    if not os.path.exists(path):
        logger.error("Path doesn't exist")
        return []

    try:
        return [fname.split(os.extsep)[0] for fname in os.listdir(path)]
    except Exception as e:
        logger.error(e)


def file_amount(folder_path) -> int:
    """ Returns file amount in a folder """
    
    _, _, files = next(os.walk(folder_path))
    logger.debug(f"File amount of {folder_path} is {len(files)}")
    return len(files)

def largest_folder(*args) -> str:
    """ Finds folder which has the most amount of files among a list of paths. """
    
    logger.debug(f"Finding largest folder")
    
    largest_folder = args[0]
    for i in range(1, len(args)):
        if file_amount(args[i]) > file_amount(largest_folder):
            largest_folder = args[i]
    logger.debug(f"Largest folder: {largest_folder}")
    return largest_folder
    