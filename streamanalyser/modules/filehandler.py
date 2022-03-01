import os
import json
import shutil
from typing import Tuple
import yaml
import gzip
import logging
import requests
import random
from shutil import copyfileobj
from datetime import datetime
from time import time

FH_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CONTEXT_PATH = os.path.join(FH_DIR_PATH, "..", "data", "default_contexts.json")


class FileHandler:
    """A class to manage cache and log files.

    Folder structure:
    Storage/
        Cache/
            Exampleid/
                messages.json.gz
                metadata.yaml
            ...
        Logs/
        Exports/
    """

    def __init__(
        self,
        storage_path,
        cache_fname="Cache",
        log_fname="Logs",
        export_fname="Exports",
        message_fname="messages.json",
        metadata_fname="metadata.yaml",
        thumbnail_fname="thumbnail.png",
        graph_fname="graph.png",
        wordcloud_fname="wordcloud.jpg",
    ):
        self.storage_path = storage_path
        self.cache_path = os.path.join(self.storage_path, cache_fname)
        self.log_path = os.path.join(self.storage_path, log_fname)
        self.export_path = os.path.join(self.storage_path, export_fname)
        self.message_fname = message_fname
        self.metadata_fname = metadata_fname
        self.thumbnail_fname = thumbnail_fname
        self.graph_fname = graph_fname
        self.wordcloud_fname = wordcloud_fname

        # create_logger is seperately implemented to prevent circular imports
        self.logger = self._create_logger(__file__)

        self.sid_path = None

    def __repr__(self) -> str:
        return "Storing files into " + self.storage_path

    def _create_logger(self, name, def_level=logging.ERROR, level=logging.DEBUG):
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        format = f"%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s"

        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        logging.basicConfig(
            level=def_level,
            format=format,
            filename=os.path.join(self.log_path, self._get_logname()),
            encoding="utf-8",
        )
        console = logging.StreamHandler()
        console.setLevel(def_level)
        console.setFormatter(logging.Formatter(format))
        logging.getLogger(name).addHandler(console)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        return logger

    def _get_logname(self) -> str:
        """Gets log name in Y-M-Wn format where n is week number, starts from 0
        Example: 2021-06-W0"""
        weekno = (
            datetime.today().isocalendar()[1]
            - datetime.today().replace(day=1).isocalendar()[1]
        )
        return datetime.today().strftime("%Y-%m-W") + str(weekno) + ".log"

    def delete_file(self, path):
        try:
            os.remove(path)
            self.logger.debug(f"{path} file removed")
        except FileNotFoundError:
            self.logger.warning(f"{path} could not be found")
        except PermissionError:
            self.logger.error(f"Access is denied to {path}. Try running in administrator mode.")
        except Exception as e:
            self.logger.critical(f"Could not remove {path} - {e.__class__.__name__}:{e}")

    def delete_dir(self, path):
        try:
            shutil.rmtree(path)
            self.logger.debug(f"{path} folder removed")
        except FileNotFoundError:
            self.logger.warning(f"{path} could not be found")
        except PermissionError:
            self.logger.error(f"Access is denied to {path}. Try running in administrator mode.")
        except Exception as e:
            self.logger.critical(f"Could not remove {path} - {e.__class__.__name__}:{e}")

    def create_dir_if_not_exists(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                self.logger.debug(f"'{path}' created")
            except PermissionError as e:
                print(
                    f"{e}\nTry another path or re-run the program in administrator mode."
                )
                self.logger.error(f"Permission denied to '{path}'")

    def create_cache_dir(self, stream_id):
        self.sid_path = os.path.join(self.cache_path, stream_id)
        self.create_dir_if_not_exists(self.sid_path)

    def cache_messages(self, message_dict):
        self.logger.info("Caching messages")
        fpath = os.path.join(self.sid_path, self.message_fname)
        try:
            with open(fpath, "w+", encoding="utf-8") as f:
                f.write(json.dumps(message_dict, ensure_ascii=False, indent=4))
        except Exception as e:
            self.delete_file(fpath)
            raise RuntimeError(f"Could not cache messages: {e.__class__.__name__}:{e}")

        self._compress_file(fpath)

    def cache_metadata(self, metadata_dict):
        self.logger.info("Caching metadata")
        fpath = os.path.join(self.sid_path, self.metadata_fname)
        try:
            with open(fpath, "w+", encoding="utf-8") as file:
                yaml.dump(
                    metadata_dict, file, default_flow_style=False, allow_unicode=True
                )
        except Exception as e:
            self.delete_file(fpath)
            raise RuntimeError(f"Could not cache metadata: {e.__class__.__name__}:{e}")

    def cache_thumbnail(self, url):
        """Alias for `download_thumbnail`"""
        self.download_thumbnail(url)

    def download_thumbnail(self, url, destination):
        self.logger.info("Downloading thumbnail")
        try:
            response = requests.get(url)
            with open(destination, "wb") as f:
                f.write(response.content)
        except Exception as e:
            self.delete_file(destination)
            raise RuntimeError(
                f"Could not download thumbnail: {e.__class__.__name__}:{e}"
            )

    def read_messages(self):
        """Reads cached messages.
        Returns a dict."""
        fpath = os.path.join(self.sid_path, self.message_fname)
        self._decompress_file(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.logger.info("Read messages")
        self._compress_file(fpath)
        return data

    def read_metadata(self):
        """Reads cached messages.
        Returns a dict."""
        fpath = os.path.join(self.sid_path, self.metadata_fname)
        self.logger.info("Read metadata")
        return yaml.load(open(fpath, "r", encoding="utf-8"), Loader=yaml.Loader)

    def _compress_file(self, jsonpath):
        """Compresses a json file with gzip"""
        try:
            with open(jsonpath, "rb") as f_in:
                with gzip.open(jsonpath + ".gz", "wb") as f_out:
                    copyfileobj(f_in, f_out)
            os.remove(jsonpath)
        except Exception as e:
            os.remove(jsonpath + ".gz")
            self.logger.critical(e)
            raise e
        self.logger.info(f"{jsonpath} compressed")

    def _decompress_file(self, jsonpath):
        """Decompresses a json gzip file"""
        try:
            with gzip.open(jsonpath + ".gz", "rb") as f_in:
                with open(jsonpath, "wb") as f_out:
                    copyfileobj(f_in, f_out)
            os.remove(jsonpath + ".gz")
        except Exception as e:
            os.remove(jsonpath)
            self.logger.critical(e)
            raise e
        self.logger.info(f"{jsonpath} decompressed")

    def clear_cache(self, cache_deletion_algorithm=None, delete_root_folder=True):
        """Clears cached files according to cache deletion
            algorithm. Default behavior is deleting the
            cache of the current session.

        Args:
            cache_deletion_algorithm (str|None, optional): Algorithm to
                delete cached files. Options are as follows:
                    - lru: Deletes least recently
                        used cache.
                    - mru: Deletes most recently
                        used cache.
                    - fifo: Deletes oldest cache.
                    - rr: Deletes random cache. (uhh...)
                If set to None, deletes cache of the current session.
                Defaults to None.

            delete_root_folder (bool, optional): Delete the folder itself too.
                Otherwise only deletes contents in the folder. Defaults to True.
        """

        self.logger.info("Clearing cache")
        self.logger.debug(f"{cache_deletion_algorithm=}")
        self.logger.debug(f"{delete_root_folder=}")

        if not cache_deletion_algorithm:
            if self.sid_path:
                try:
                    shutil.rmtree(self.sid_path)
                    self.logger.debug(f"Deleted '{self.sid_path}'")
                    if not delete_root_folder:
                        os.makedirs(self.sid_path)
                except Exception as e:
                    self.logger.error(e)
            return

        if cache_deletion_algorithm == "mru":
            dir_to_delete = self.most_recently_used_folder(self.cache_path)
        elif cache_deletion_algorithm == "lru":
            dir_to_delete = self.least_recently_used_folder(self.cache_path)
        elif cache_deletion_algorithm == "fifo":
            dir_to_delete = self.oldest_folder(self.cache_path)
        elif cache_deletion_algorithm == "rr":
            dir_to_delete = self.random_folder(self.cache_path)
        else:
            self.logger.error(
                "Invalid deletion algorithm: {}".format(cache_deletion_algorithm)
            )
            raise ValueError(
                "Invalid deletion algorithm: {}".format(cache_deletion_algorithm)
            )

        path = os.path.join(self.cache_path, dir_to_delete)
        try:
            shutil.rmtree(path)
            self.logger.debug(f"Deleted '{self.sid_path}'")
            if not delete_root_folder:
                os.makedirs(path)
        except Exception as e:
            self.logger.error(e)

    def check_integrity(self, cache_path=None, autofix=False) -> Tuple[list, list]:
        """Checks integrity of the cached files.
        Note that it detects files by their names, not content.

        Args:
            cache_path (str|None, optional): Path to the cache files
                of a stream. Defaults to None, which sets the path to
                the current stream id.

            autofix (bool, optional): Attempts to automatically fix issues
                by deleting unnecessary files and compressing uncompressed
                messages. Missing files must be dealt manually.
                Defaults to False.

        Returns:
            Tuple[list, list]: Lists of unnecesary and missing files
        """

        self.logger.info("Checking cache integrity")
        self.logger.debug(f"{cache_path=}")
        self.logger.debug(f"{autofix=}")

        if not cache_path:
            cache_path = self.sid_path

        files = self.get_filenames(cache_path, show_extension=True)
        necessary_files = [
            self.message_fname + ".gz",
            self.metadata_fname,
        ]
        unnecesary_files = list(set(files) - set(necessary_files))
        missing_files = list(set(necessary_files) - set(files))

        self.logger.debug(f"{unnecesary_files=}")
        self.logger.debug(f"{missing_files=}")

        if autofix:
            for folder in os.listdir(self.cache_path):
                full_path = os.path.join(self.cache_path, folder)
                try:
                    for _, _, files in os.walk(full_path):
                        pass
                    if os.stat(full_path).st_size == 0 and len(files) == 0:
                        self.delete_dir(full_path)
                except AttributeError:
                    continue
            for file in unnecesary_files:
                # it might be a json file that is not compressed
                if file == self.message_fname:
                    self._compress_file(os.path.join(cache_path, file))
                    missing_files.remove(file + ".gz")
                    continue
                self.delete_file(os.path.join(cache_path, file))
            unnecesary_files = []

        return missing_files, unnecesary_files

    def get_filenames(self, path, show_extension=False) -> list[str]:
        """Returns file names in a path"""

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

    def get_foldernames(self, path) -> list[str]:
        """Returns folder names in a path"""

        self.logger.info(f"Finding folder names in {path}")
        try:
            return next(os.walk(path))[1]
        except Exception as e:
            self.logger.error(e)
            raise e

    def _creation_time_in_days(self, path) -> int:
        """Returns difference between the creation time and
        the current time of the file in days"""

        if os.path.isfile(path):
            ctime = os.path.getctime(path)
            days = datetime.fromtimestamp(int(time() - ctime)).strftime("%d")
            return int(days)
        self.logger.debug(f"{path} is not a file")
        return 0

    def _delete_old_files(self, folder_path, time_limit_in_days):
        """Delete files in a folder older than the time limit."""

        for name in os.listdir(folder_path):
            fpath = os.path.join(folder_path, name)
            if self._creation_time_in_days(fpath) >= time_limit_in_days:
                self.delete_file(fpath)

    def file_amount(self, folder_path) -> int:
        """Returns file amount in a folder"""

        _, _, files = next(os.walk(folder_path))
        self.logger.debug(f"File amount in {folder_path} is {len(files)}")
        return len(files)

    def dir_amount(self, folder_path) -> int:
        """Returns folder amount in a folder"""

        _, dirs, _ = next(os.walk(folder_path))
        self.logger.debug(f"Folder amount in {folder_path} is {len(dirs)}")
        return len(dirs)

    def least_recently_used_folder(self, fpath) -> str:
        """Returns least recenty used folder in path
        by checking last access time of the
        message file inside the folder"""

        least_recently_used_folder = None
        last_access_time = time()

        for root, dirs, _ in os.walk(fpath):
            for dname in dirs:
                if os.path.join(root, dname) == self.sid_path:
                    continue
                try:
                    path = os.path.join(root, dname, self.message_fname + ".gz")
                except:
                    try:
                        self.check_integrity(
                            cache_path=os.path.join(root, dname), autofix=True
                        )
                        path = os.path.join(root, dname, self.message_fname + ".gz")
                    except:
                        msg = "Message cache couldn't be found"
                        self.logger.error(msg)
                        raise Exception(msg)
                if os.path.getatime(path) < last_access_time:
                    last_access_time = os.path.getatime(path)
                    least_recently_used_folder = dname
        self.logger.debug(
            "Least recently used id: {} ({})".format(
                least_recently_used_folder, last_access_time
            )
        )
        return least_recently_used_folder

    def most_recently_used_folder(self, fpath) -> str:
        """Returns most recenty used folder in path
        by checking last access time of the
        message file inside the folder"""

        most_recently_used_folder = None
        last_access_time = 0

        for root, dirs, _ in os.walk(fpath):
            for dname in dirs:
                if os.path.join(root, dname) == self.sid_path:
                    continue
                try:
                    path = os.path.join(root, dname, self.message_fname + ".gz")
                except:
                    try:
                        self.check_integrity(
                            cache_path=os.path.join(root, dname), autofix=True
                        )
                        path = os.path.join(root, dname, self.message_fname + ".gz")
                    except:
                        msg = "Message cache couldn't be found"
                        self.logger.error(msg)
                        raise Exception(msg)
                if os.path.getatime(path) > last_access_time:
                    last_access_time = os.path.getatime(path)
                    most_recently_used_folder = dname
        self.logger.debug(
            "Most recently used id: {} ({})".format(
                most_recently_used_folder, last_access_time
            )
        )
        return most_recently_used_folder

    def oldest_folder(self, fpath) -> str:
        """Returns oldest folder in path"""

        oldest_folder = None
        creation_time = time()

        for root, dirs, _ in os.walk(fpath):
            for dname in dirs:
                if os.path.join(root, dname) == self.sid_path:
                    continue
                path = os.path.join(root, dname)
                if os.path.getctime(path) < creation_time:
                    creation_time = os.path.getctime(path)
                    oldest_folder = dname

        self.logger.debug(f"Oldest folder: {oldest_folder} ({creation_time})")
        return oldest_folder

    def random_folder(self, fpath) -> str:
        """Returns a random folder in cache path"""
        for root, dirs, _ in os.walk(fpath):
            if len(dirs) == 1:
                return dirs[0]
            while True:
                choice = random.choice(dirs)
                if os.path.join(root, choice) != self.sid_path:
                    break
            self.logger.debug(f"Random folder: {choice}")
            return choice

    def is_cached(self, sid=None) -> bool:
        """Returns False if all necessary files are absent"""

        self.logger.info("Checking if cached")
        self.logger.debug(f"{sid=}")

        if sid:
            path = os.path.join(self.cache_path, sid)
        else:
            path = self.sid_path

        files = self.get_filenames(path, show_extension=True)
        necessary_files = [
            self.message_fname + ".gz",
            self.metadata_fname,
        ]
        missing_files = list(set(necessary_files) - set(files))

        self.logger.debug(f"is_cached: {(not len(missing_files) == 2)}")
        return not len(missing_files) == 2

    def get_cached_ids(self) -> list[str]:
        """Returns list of cached ids"""
        return [f for f in self.get_foldernames(self.cache_path) if self.is_cached(f)]

    def add_context(self, reaction_to, phrases):
        """Add new context. Note that it does not check
        if the context already exists

        Args:
            reaction_to (str): What is the reaction for.
            phrases (list[dict]): Phrase list for the reaction.
                Each element should be a dictionary that contains:
                - phrase (str): Phrase that triggers the reaction.
                - is_exact (boolean): If the message should be exactly the same
                    or should only include it.

                example: `[{phrase:"lol", is_exact:False}]`
        """
        self.logger.info("Adding new context")
        self.logger.debug(f"{reaction_to=}")
        self.logger.debug(f"{phrases=}")

        new_context = {
            "reaction_to": reaction_to,
            "triggers": [
                {"phrase": phrase["phrase"], "is_exact": phrase["is_exact"]}
                for phrase in phrases
            ],
        }
        with open(CONTEXT_PATH, "r+", encoding="utf-8") as file:
            contexts = list(json.load(file))
            contexts.append(new_context)
            file.seek(0)
            file.write(json.dumps(contexts, indent=4, ensure_ascii=False))

    def remove_context(self, reaction_to):
        """Remove a context
        Args:
            reaction_to (str): Reaction to be deleted.
        """
        self.logger.info("Removing context")
        self.logger.debug(f"{reaction_to=}")

        with open(CONTEXT_PATH, "r", encoding="utf-8") as file:
            contexts = list(json.load(file))
        for i in range(len(contexts)):
            if contexts[i]["reaction_to"] == reaction_to:
                del contexts[i]
                break
        with open(CONTEXT_PATH, "w", encoding="utf-8") as file:
            file.write(json.dumps(contexts, indent=4, ensure_ascii=False))

    def open_cache_folder(self, sid):
        target_path = os.path.join(self.cache_path, sid)
        try:
            os.startfile(target_path)
            self.logger.info(f"Opened {target_path} in file explorer")
        except FileNotFoundError:
            self.logger.error(f"Could not find {target_path}")
