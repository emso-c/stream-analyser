from collections import Counter
from datetime import timedelta
import os
import random
import traceback
from shutil import copyfile
from typing import Tuple
from time import time
from colorama.ansi import Back, Style

from wordcloud import WordCloud

from .modules import (
    loggersetup,
    filehandler,
    datacollector,
    datarefiner,
    chatanalyser,
    structures,
    utils
)

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_FONT_PATH = os.path.join(DIR_PATH, "fonts", "NotoSansCJKjp-Bold.ttf")

class StreamAnalyser():
    """ A class that analyses live streams.

    Args:
        sid (str): Video id of the stream.

        msglimit (int|None, optional): Message amount to fetch. Defaults to None.

        res_lvl (int, optional): Resolution level of the thumbnail.
            Resolution levels are sorted by quality with 0 being lowest
            and 3 being highest. Defaults to 2.

        verbose (bool, optional): Print output to console. Defaults to False.

        disable_logs (bool, optional): Disable logging for debugging purposes.
            Log files' location can be found in `filehandler` module. 
            Defaults to False.

        keep_logs (bool, optional): Do not delete logs. See `log_duration`
            for more information. Defaults to False.

        log_duration (int, optional): Log duration in days. Logs that are
            older than this value will be deleted if `keep_logs` option is
            False. Cache of the week can only be deleted after 7 days.
            Defaults to 15.

        not_cache(bool, optional): Not cache stream data when using
            `analyse` function.
            Isn't recommended to use since fetching live chat messages
            takes quite a lot of time. The mere use-case is if the data
            will be used only for once. Even so, the cache can be deleted
            later with the `clear_cache` function. Defaults to False.

        keep_cache (bool, optional): Do not delete any of the 
            cached files, anytime. Isn't recommended to use since
            lots of cached data might take up unnecessary space
            if not handled. If set to False, cached data will be
            deleted occasionally according to the chosen algorithm.
            See `cache_deletion_algorithm` for more info.
            Defaults to False.

        cache_deletion_algorithm (str, optional): Algorithm to delete
            cached files. Options are as follows:
                - lru (Least recently used): Deletes least recently
                    used cache. (recommended)
                - mru (Most recently used): Deletes most recently
                    used cache, which is the current sessions cache.
                - fifo (First in first out): Deletes oldest cache.
                - rr (Random replacement): Deletes random cache. (uhh...)
            Defaults to 'lru'.
        
        cache_limit (int, optional): Cache file amount to keep. Cached
            files will be deleted if file amount exceeds this value
            according to `cache_deletion_algorithm` option. Defaults to 20.
    """

    def __init__(
            self, sid, msglimit=None, verbose=False, thumb_res_lvl = 2,
            disable_logs = False, keep_logs=False, log_duration=15,
            not_cache=False, keep_cache=False, cache_deletion_algorithm='lru',
            cache_limit = 20
        ):

        self.sid = sid
        self.msglimit = msglimit
        self.verbose = verbose
        self.thumb_res_lvl = thumb_res_lvl
        self.disable_logs = disable_logs
        self.not_cache = not_cache
        self.keep_cache = keep_cache
        self.cache_limit = cache_limit

        self._raw_messages = {}
        self.messages = []
        self.authors = []
        self.highlights = []
        self.context_path = chatanalyser.CONTEXT_PATH
        self.metadata = {}
        self.wordcloud = None
        self.fig = None
        self.logger = loggersetup.create_logger(__file__, sid=sid)
        self.filehandler = filehandler.streamanalyser_filehandler
        self.collector = datacollector.DataCollector(
            sid, msglimit, verbose
        )
        self.refiner = datarefiner.DataRefiner(self.verbose)
        self.canalyser = None

        if disable_logs:
            self._disable_logs()

        if not keep_logs:
            self.filehandler.delete_old_files(
                self.filehandler.log_path, log_duration
            )
        self.logger.info("Session start ==================================")
        self.filehandler.create_cache_dir(self.sid)
        famount = self.filehandler.dir_amount(
            self.filehandler.cache_path
        )
        if famount > cache_limit:
            self.logger.warning(f"Cache limit has been exceeded by {famount-cache_limit}")
        while famount > cache_limit:
            self.clear_cache(cache_deletion_algorithm)
            famount -= 1


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)

    def _disable_logs(self):
        self.logger.disabled = True
        self.filehandler.logger.disabled = True
        self.collector.logger.disabled = True
        self.refiner.logger.disabled = True

    def _cache_metadata(self, metadata):
        self.filehandler.cache_metadata(metadata)
    
    def _cache_messages(self, raw_messages):
        self.filehandler.cache_messages(raw_messages)

    def _cache_thumbnail(self, thumbnail_url):
        self.filehandler.download_thumbnail(thumbnail_url)

    def clear_cache(self, cache_deletion_algorithm=None):
        self.filehandler.clear_cache(cache_deletion_algorithm)

    def collect_data(self):
        """ Collects and caches stream data:
            - metadata (title, channel etc.)
            - messages
            - thumbnail
        """
        # collect data
        metadata = self.collector.collect_metadata()
        raw_messages = self.collector.fetch_raw_messages()
        thumbnail_url = self.collector.get_thumbnail_url(self.thumb_res_lvl)

        # cache data
        self._cache_metadata(metadata)
        self._cache_messages(raw_messages)
        self._cache_thumbnail(thumbnail_url)

    def read_data(self):
        """ Reads cached data """
        self._raw_messages = self.filehandler.read_messages()
        self.metadata.update(self.filehandler.read_metadata())
        
    def refine_data(self):
        """ Refines read data """
        self.messages = self.refiner.refine_raw_messages(
            self._raw_messages,
            self.msglimit
        )
        # we don't need raw messages anymore
        # empty them so they don't take up space
        self._raw_messages = None
        self.authors = self.refiner.get_authors()

    def analyse_data(self):
        """ Analyses refined data and finds highligths """
        #TODO Add other arguments too
        canalyser = chatanalyser.ChatAnalyser(
            refined_messages = self.messages,
            stream_id = self.sid,
            context_path = self.context_path,
            verbose = self.verbose
        )
        if self.disable_logs:
            canalyser.logger.disabled = True
        canalyser.analyse(graph_title=self.metadata["title"])
        self.highlights = canalyser.highlights
        self.fig = canalyser.fig

    def analyse(self):
        if not self.is_cached:
            self.collect_data()
        self.enforce_integrity()
        self.read_data()
        self.refine_data()
        self.analyse_data()
        if self.not_cache:
            self.clear_cache()

    def _check_integrity(self, autofix=False) -> Tuple[list, list]:
        return self.filehandler.check_integrity(autofix=autofix)

    @property
    def is_cached(self):
        return not any(self._check_integrity())

    def enforce_integrity(self):
        """ Enforces file integrity by recollecting missing
            data and deleting unnecessary cache files """

        missing_files, _ = self._check_integrity(
            autofix = True
        )
        for missing_file in missing_files:
            if missing_file == self.filehandler.message_fname+".gz":
                self.logger.warning("Message file is missing")
                self.filehandler.cache_messages(
                    self.collector.fetch_raw_messages()
                )
            if missing_file == self.filehandler.metadata_fname:
                self.logger.warning("Metadata file is missing")
                self.filehandler.cache_metadata(
                    self.collector.collect_metadata()
                )
            if missing_file == self.filehandler.thumbnail_fname:
                self.logger.warning("Thumbnail file is missing")
                self.filehandler.download_thumbnail(
                    self.collector.get_thumbnail_url(
                        self.thumb_res_lvl
                    )
                )

        # TODO reimplement add fetch missing messages feature

    def generate_wordcloud(self, font_path=None, scale=3) -> WordCloud:
        """ Returns word cloud of the stream

        Args:
            font_path (str, optional): Custom font path. Defaults to None.
            scale (int, optional): Scale of the resulting wordcloud.
                Might want to decrease it for more performance. Defaults to 3.
        """

        #TODO Stylize the wordcloud

        self.logger.info("Generating word cloud")
        self.logger.debug(f"{font_path=}")
        self.logger.debug(f"{scale=}")

        if self.verbose:
            print("Generating word cloud...", end='\r')
        
        if not font_path:
            font_path = DEFAULT_FONT_PATH
        
        # get all words from the chat
        wordlist = [msg.text.replace("_","") for msg in self.messages]
        
        # shuffle word list to minimize the issue where repeating
        # consecutive messages merge together in the word cloud
        random.shuffle(wordlist)
        
        word_cloud = WordCloud(
            font_path = font_path,
            scale = scale
        ).generate(" ".join(wordlist))

        if self.verbose:
            print("Generating word cloud... done")
        self.wordcloud = word_cloud
        return self.wordcloud

    def find_messages(self, search_phrase, exact=False, ignore_case=True) -> list[structures.Message]:
        """ Finds messages containing a specific phrase or exactly the same phrase.

        Args:
            search_phrase (str): The phrase to search.
            exact (bool, optional): If the phrase has to be exactly the same or not. Defaults to False.
            ignore_case (bool, optional): Ignore letter cases. Defaults to True.

        Returns:
            list[Message]: List of messages that contains the given phrase.
        """
        
        messages_to_return = []
        self.logger.info("Finding messages")
        self.logger.debug(f"{search_phrase=}")
        self.logger.debug(f"{exact=}")
        self.logger.debug(f"{ignore_case=}")

        if ignore_case:
            search_phrase = search_phrase.lower()

        tmp_message = None
        for original_message in self.messages:
            tmp_message = original_message.text
            if ignore_case:
                tmp_message = tmp_message.lower()
            if  (exact and search_phrase == tmp_message) or \
                (not exact and search_phrase in tmp_message):
                messages_to_return.append(original_message)
        return messages_to_return

    def find_user_messages(self, username=None, id=None) -> list[structures.Message]:
        """ Finds messages by either username or user id.

        Args:
            username (str, optional): Target username. Defaults to None.
                Note that it's more reliable to use id since there might 
                be same users with the same name or username changes.

            id (str, optional): Target user id. Defaults to None.

        Raises:
            ValueError: Should provide either username or id.

        Returns:
            list[Message]: Messages the user typed.
        """

        self.logger.info("Finding user messages")
        self.logger.debug(f"{id=}")
        self.logger.debug(f"{username=}")

        if not username and not id:
            self.logger.error("Should provide either username or id")
            raise ValueError("Should provide either username or id.")
        if username and id:
            self.logger.warning("Should only provide one argument. Moving on with id.")
            username=None

        messages_to_return = []
        for message in self.messages:
            if  (id and message.author.id == id) or \
                (username and message.author.name == username):
                messages_to_return.append(message)

        return messages_to_return

    def most_used_phrase(self, exclude=[], normalize=True) -> Tuple[str, int]:
        """ Returns most frequently used phrase

        Args:
            exclude (list, optional): List of words to exclude from the search.
                Defaults to [].

            normalize (bool, optional): Option for the word be normalized 
                to cover more instances. Defaults to True.

        Returns:
            Tuple[str, int]: Most used word and it's frequency 
        """

        #return "草"    # would probably work lol

        self.logger.info("Finding most used word")
        self.logger.debug(f"{exclude=}")
        self.logger.debug(f"{normalize=}")
        
        if isinstance(exclude, str):
            exclude = list(exclude)
        
        _words = []
        for message in self.messages:
            _words.extend(message.text.split(' '))

        if normalize:
            _words = [utils.normalize(word) for word in _words]
        
        _idx = 0
        while exclude and Counter(_words).most_common(1+_idx)[_idx][0] in exclude:
            _idx+=1
            if _idx == len(_words)-1:
                return Counter(_words).most_common(1+_idx)[_idx]

        self.logger.debug(f"Most used phrase: {Counter(_words).most_common(1+_idx)[_idx]}")
        return Counter(_words).most_common(1+_idx)[_idx]

    @property
    def total_message_amount(self):
        return len(self.messages)

    def export_data(self, folder_name=None, path=None, open_folder=False):
        """ Exports the analysed data to the path.

        Args:
            folder_name (str|None, optional): File name to export the results. Defaults to None,
                which exports data under the file named current UNIX timestamp.
            path (str|None, optional): Path to export the results. Defaults to None,
                which exports data to the default path.
            open_folder (bool, optional): Open the export folder in file explorer
                after exporting. Defaults to false

        """

        self.logger.info("Exporting data")
        self.logger.debug(f"{folder_name=}")
        self.logger.debug(f"{path=}")

        if not path:
            path = self.filehandler.export_path
        
        try:
            self.filehandler.create_dir_if_not_exists(path)
        except PermissionError as pe:
            self.logger.error(pe)
            return
        
        if not folder_name:
            folder_name = str(int(time()))
        else:
            # check if there's already a file with the same name
            # if so, add UNIX timestamp to make it unique
            for name in os.listdir(path):
                if os.path.isdir(os.path.join(path, name)) and name == folder_name:
                    folder_name = folder_name+'_'+str(int(time()))
                    warn_msg = f"{name} already exists, renaming to {folder_name}"
                    self.logger.warning(warn_msg)
                    break

        target_path = path+'\\'+folder_name
        self.filehandler.create_dir_if_not_exists(target_path)
        
        # export messages
        self.filehandler._decompress_file(
            os.path.join(self.filehandler.sid_path, self.filehandler.message_fname)
        )
        copyfile(
            src=os.path.join(self.filehandler.sid_path, self.filehandler.message_fname), 
            dst=os.path.join(target_path, self.filehandler.message_fname), 
        )
        self.filehandler._compress_file(
            os.path.join(self.filehandler.sid_path, self.filehandler.message_fname)
        )
        self.logger.info("Exported messages")

        # export metadata
        copyfile(
            src=os.path.join(self.filehandler.sid_path, self.filehandler.metadata_fname), 
            dst=os.path.join(target_path, self.filehandler.metadata_fname), 
        )
        self.logger.info("Exported metadata")

        # export thumbnail
        copyfile(
            src=os.path.join(self.filehandler.sid_path, self.filehandler.thumbnail_fname), 
            dst=os.path.join(target_path, self.filehandler.thumbnail_fname), 
        )
        self.logger.info("Exported thumbnail")

        # export word cloud
        if self.messages:
            self.generate_wordcloud().to_file(
                os.path.join(target_path, 'wordcloud.jpg')
            )
            self.logger.info("Exported wordcloud")

        # export highlights
        if self.highlights:
            hl_path = os.path.join(target_path, "highlights.txt")
            with open(hl_path, 'w', encoding='utf-8') as file:
                file.writelines([hl.colorless_str+'\n' for hl in self.highlights])
            self.logger.info("Exported highlights")

        #TODO fix empty export
        #TODO export graph
        if self.fig:
            self.fig.savefig(os.path.join(target_path, 'graph.png'))
            self.logger.info("Exported graph")

        if open_folder:
            try:
                os.startfile(target_path)
                self.logger.info(f"Opened {target_path} in file explorer")
            except FileNotFoundError:
                self.logger.error(f"Couldn't find {target_path}")

    def print_summary(self, top=None, intensity_filters=[]) -> list[structures.Highlight]:
        """ Only prints time and intensity of the highlights.

        Args:
            top (int, optional): Top n highlights to print, sorted by intensity. 
                Defaults to None, which returns all.
            intensity_filters (list[str]): Intensity levels to filter out. Defaults to [].

        Returns:
            list[Highlight]: list of printed highlights
        """
        
        self.logger.info("Printing summary")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        highlights_to_return = []
        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Summary:"+Style.RESET_ALL)
        for _count, highlight in enumerate(highlights):
            if not highlight.intensity in intensity_filters:
                print(f'{timedelta(seconds=int(highlight.time))}: {highlight.intensity.colored_level}')
                highlights_to_return.append(highlight)
                self.logger.debug(highlight.colorless_str)

                if top and _count == top:
                    return highlights_to_return

        return highlights_to_return

    def print_highlights(self, top=None, include=[], 
                not_include=[], intensity_filters=[]) -> list[structures.Highlight]:
        """ Prints found highlights.

        Args:
            top (int, optional): Top n highlights to print, sorted by intensity. 
                Defaults to None, which returns all.
            include (list[str], optional): List of reactions to see. Defaults to [].
                Reaction names can be found in `context.json`.
            not_include (list[str], optional): List of reactions to not see. 
                Overrides include. Defaults to [].
                Reaction names can be found in `context.json`.
            intensity_filters (list[str]): Intensity levels to filter out. Defaults to [].

        Returns:
            list[Highlight]: List of printed highlights

        """

        self.logger.info("Printing highlights")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        _count = 0
        highlights_to_return = []
        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Highlights:"+Style.RESET_ALL)
        for highlight in highlights:
            skip = False
            for context in highlight.contexts:
                if not_include and context in not_include:
                    skip = True
                    break
            if skip:
                continue
            for context in highlight.contexts:
                if (include and context in include) or not include:
                    if not highlight.intensity.level in intensity_filters:
                        print(highlight)
                        highlights_to_return.append(highlight)
                        self.logger.debug(highlight.colorless_str)
                        _count+=1
                        if top and _count == top:
                            return highlights_to_return
                        break
        
        return highlights_to_return

    def print_urls(self, top=None, intensity_filters=[])  -> list[structures.Highlight]:
        """ Prints urls of highlights (with timestamps)

            args:
                top (int, optional): Top n highlights to print, sorted by intensity.
                    Defaults to None, which returns all.
                intensity_filters (list[str]): Intensity levels to filter out.
                    Defaults to [].

            example:
            >>> analyserObject.show_urls():
            >>> "00:02:12 -> https://youtu.be/wAPCSnAhhC8?t=132"
        """
        
        self.logger.info("Printing url's")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        highlights_to_return = []

        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Links:"+Style.RESET_ALL)
        for _count, hl in enumerate(highlights):
            if not hl.intensity.level in intensity_filters:
                print(hl.intensity.color+str(timedelta(seconds=int(hl.time)))+Style.RESET_ALL, '->' ,hl.url)
                self.logger.debug(f"{str(timedelta(seconds=int(hl.time)))} -> {hl.url}")
                highlights_to_return.append(hl)
                if top and _count == top:
                    return highlights_to_return

        return highlights_to_return

    def show_graph(self):
        self.fig.show()
