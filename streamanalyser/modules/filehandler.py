import os
import json
import shutil
import yaml
import gzip
import logging
import requests
from shutil import copyfileobj
from datetime import datetime


class FileHandler():
    """ A class to manage cache and log files. 
    
    Folder structure:
    Storage/
        Cache/
            Exampleid/
                messages.json
                metadata.yaml
                thumbnail.jpg
            ...
        Logs/
    
    """
    
    def __init__(
            self,
            storage_path,
            cache_fname='Cache',
            log_fname='Logs',
            message_fname = 'messages.json',
            metadata_fname = 'metadata.yaml',
            thumbnail_fname = 'thumbnail.png',
        ):
        self.storage_path = storage_path
        self.cache_path = os.path.join(self.storage_path, cache_fname)
        self.log_path = os.path.join(self.storage_path, log_fname)
        self.message_fname = message_fname
        self.metadata_fname = metadata_fname
        self.thumbnail_fname = thumbnail_fname

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
        except Exception as e:
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
        return data

    def read_metadata(self):
        """ Reads cached messages.
            Returns a dict. """
        fpath = os.path.join(self.sid_path, self.metadata_fname)
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

    def show_cached(self):
        pass


streamanalyser_filehandler = FileHandler(
    storage_path='C:\\Stream Analyser'
)