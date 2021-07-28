import os
import json
import shutil
from typing import Tuple
import yaml
import gzip
import logging
import requests
from shutil import copyfileobj
from datetime import datetime
from time import time


class FileHandler():
    """ A class to manage cache and log files. 
    
    Folder structure:
    Storage/
        Cache/
            Exampleid/
                messages.json.gz
                metadata.yaml
                thumbnail.jpg
            ...
        Logs/
        Exports/
    
    """
    
    def __init__(
            self,
            storage_path,
            cache_fname='Cache',
            log_fname='Logs',
            export_fname='Exports',
            message_fname = 'messages.json',
            metadata_fname = 'metadata.yaml',
            thumbnail_fname = 'thumbnail.png',
            graph_fname = 'graph.png',
            wordcloud_fname = 'wordcloud.jpg'
        ):
        self.storage_path = storage_path
        self.cache_path = os.path.join(self.storage_path, cache_fname)
        self.log_path = os.path.join(self.storage_path, log_fname)
        self.export_path = os.path.join(self.storage_path, export_fname)
        self.message_fname = message_fname
        self.metadata_fname = metadata_fname
        self.thumbnail_fname = thumbnail_fname
        self.graph_fname = metadata_fname
        self.wordcloud_fname = metadata_fname

        # create_logger is seperately implemented to prevent circular imports
        self.logger = self._create_logger(__file__)

        self.sid_path = None

    def __repr__(self) -> str:
        return "Storing files into "+self.project_path

    def _create_logger(self, name, def_level=logging.ERROR, level=logging.DEBUG):
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s'
        
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        logging.basicConfig(
            level=def_level,
            format=format,
            filename=os.path.join(
                self.log_path, 
                self._get_logname()
            ),
            encoding='utf-8',
        )
        console = logging.StreamHandler()
        console.setLevel(def_level)
        console.setFormatter(logging.Formatter(format))
        logging.getLogger(name).addHandler(console)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        return logger

    def _get_logname(self) -> str:
        """ Gets log name in Y-M-Wn format where n is week number, starts from 0
            Example: 2021-06-W0 """
        weekno = datetime.today().isocalendar()[1] - datetime.today().replace(day=1).isocalendar()[1]
        return datetime.today().strftime('%Y-%m-W')+str(weekno)+".log"
        
    def delete_file(self, path):
        try:
            os.remove(path)
            self.logger.info(f'{path} removed')
        except FileNotFoundError:
            self.logger.debug(f"{path} could not be found")
        except Exception:
            self.logger.error(f"Could not remove {path}")

    def create_dir_if_not_exists(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                self.logger.debug(f"'{path}' created")
            except PermissionError as e:
                print(f"{e}\nTry another path or re-run the program in administrator mode.")
                self.logger.error(f"Permission denied to '{path}'")

    def create_cache_dir(self, stream_id):
        self.sid_path = os.path.join(self.cache_path, stream_id)
        self.create_dir_if_not_exists(self.sid_path)

    def cache_messages(self, message_dict):
        self.logger.info("Caching messages")
        fpath = os.path.join(self.sid_path, self.message_fname)
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(message_dict, ensure_ascii=False, indent=4))
        except Exception as e:
            self.delete_file(fpath)
            raise RuntimeError(f"Could not cache messages: {e.__class__.__name__}:{e}")

        self._compress_file(fpath)

    def cache_metadata(self, metadata_dict):
        self.logger.info("Caching metadata")
        fpath = os.path.join(self.sid_path, self.metadata_fname)
        try:
            with open(fpath, 'w', encoding='utf-8') as file:
                yaml.dump(metadata_dict, file, default_flow_style=False)
        except Exception as e:
            self.delete_file(fpath)
            raise RuntimeError(f"Could not cache metadata: {e.__class__.__name__}:{e}")

    def cache_thumbnail(self, url):
        fpath = os.path.join(self.sid_path, self.thumbnail_fname)
        self.logger.info("Downloading thumbnail")
        try:
            response = requests.get(url)
            with open(fpath, "wb") as f:
                f.write(response.content)
        except Exception as e:
            self.delete_file(fpath)
            raise RuntimeError(f"Could not download thumbnail: {e.__class__.__name__}:{e}")

    def download_thumbnail(self, url):
        """ Alias for cache_thumbnail """
        self.cache_thumbnail(url)

    def read_messages(self):
        """ Reads cached messages.
            Returns a dict. """
        fpath = os.path.join(self.sid_path, self.message_fname)
        self._decompress_file(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.logger.info("Read messages")
        self._compress_file(fpath)
        return data

    def read_metadata(self):
        """ Reads cached messages.
            Returns a dict. """
        fpath = os.path.join(self.sid_path, self.metadata_fname)
        self.logger.info("Read metadata")
        return yaml.load(open(fpath, 'r'), Loader=yaml.Loader)

    def _compress_file(self, jsonpath):
        """ Compresses a json file with gzip """
        try:
            with open(jsonpath, 'rb') as f_in:
                with gzip.open(jsonpath+".gz", 'wb') as f_out:
                    copyfileobj(f_in, f_out)
            os.remove(jsonpath)
        except Exception as e:
            os.remove(jsonpath+".gz")
            self.logger.critical(e)
            raise e
        self.logger.info(f'{jsonpath} compressed')

    def _decompress_file(self, jsonpath):
        """ Decompresses a json gzip file """
        try:
            with gzip.open(jsonpath+'.gz', 'rb') as f_in:
                with open(jsonpath, 'wb') as f_out:
                    copyfileobj(f_in, f_out)
            os.remove(jsonpath+'.gz')
        except Exception as e:
            os.remove(jsonpath)
            self.logger.critical(e)
            raise e
        self.logger.info(f'{jsonpath} decompressed')

    def clear_cache(self):
        """ Clears cached files """
        if not self.sid_path:
            self.logger.warning("Cache path could not be found")
        try:
            shutil.rmtree(self.sid_path)
        except Exception as e:
            self.logger.error(e)

    def check_integrity(self, autofix=False) -> Tuple[list, list]:
        """ Checks integrity of the cached files. Note that it
            only detects files by their names, not content.

        Args:
            autofix (bool, optional): Attempts to automatically fix issues
                by deleting unnecessary files and compressing uncompressed
                messages. Missing files must be dealt manually.
                Defaults to False.

        Returns:
            Tuple[list, list]: Lists of unnecesary and missing files
        """

        self.logger.info("Checking cache integrity")
        self.logger.debug(f"{autofix=}")
        
        files = self.get_filenames(self.sid_path, show_extension=True)
        necessary_files = [self.message_fname+".gz",
                           self.metadata_fname,
                           self.thumbnail_fname]
        unnecesary_files = list(set(files) - set(necessary_files))
        missing_files = list(set(necessary_files) - set(files))

        self.logger.debug(f"{unnecesary_files=}")
        self.logger.debug(f"{missing_files=}")
        
        if autofix:
            for file in unnecesary_files:                
                # it might be a json file that is not compressed
                if file == self.message_fname:
                    self._compress_file(os.path.join(self.sid_path, file))
                    missing_files.remove(file+".gz")
                    continue
                self.delete_file(os.path.join(self.sid_path, file))
            unnecesary_files = []

        return missing_files, unnecesary_files

    def get_filenames(self, path, show_extension=False) -> list[str]:
        """ Returns file names in a path """

        self.logger.info(f"Finding file names in {path}")
        if not os.path.exists(path):
            self.logger.error("Path doesn't exist")
            return []

        try:
            if show_extension:
                return [fname for fname in os.listdir(path)]
            return [fname.split(os.extsep)[0] for fname in os.listdir(path)]
        except Exception as e:
            self.logger.error(e)

    # TODO test these new functions
    def _creation_time_in_days(self, path) -> int:
        """ Returns difference between the creation time and
            the current time of the file in days """

        if os.path.isfile(path):
            ctime = os.path.getctime(path)
            days = datetime.fromtimestamp(int(time()-ctime)).strftime('%d')
            return int(days)
        self.logger.debug(f"{path} is not a file")
        return 0

    def delete_old_files(self, folder_path, time_limit_in_days):
        """ Delete files in a folder older than the time limit. """

        for name in os.listdir(folder_path):
            fpath = os.path.join(folder_path, name)
            if self._creation_time_in_days(fpath) >= time_limit_in_days:
                self.delete_file(fpath)

    def file_amount(self, folder_path) -> int:
        """ Returns file amount in a folder """

        _, _, files = next(os.walk(folder_path))
        self.logger.debug(f"File amount in {folder_path} is {len(files)}")
        return len(files)

    def largest_folder(self, *args) -> str:
        """ Finds folder which has the most amount
            of files among a list of paths. """
        
        self.logger.debug(f"Finding largest folder")
        
        largest_folder = args[0]
        for i in range(1, len(args)):
            if self.file_amount(args[i]) > self.file_amount(largest_folder):
                largest_folder = args[i]
        self.logger.debug(f"Largest folder: {largest_folder}")
        return largest_folder

streamanalyser_filehandler = FileHandler(
    storage_path='C:\\Stream Analyser'
)