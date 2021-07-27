from collections import Counter
import os
import random
import traceback
from typing import Tuple

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
    """[summary]
    """

    def __init__(
            self, sid, msglimit=None, disable_logs = False, thumb_res_lvl = 2,
            verbose=False
        ):

        self.sid = sid
        self.msglimit = msglimit
        self.disable_logs = disable_logs
        self.thumb_res_lvl = thumb_res_lvl
        self.verbose = verbose

        self.metadata = {}
        self._raw_messages = {}
        self.messages = []
        self.authors = []
        self.highlights = []
        self.context_path = chatanalyser.CONTEXT_PATH
        
        self.logger = loggersetup.create_logger(__file__, sid=sid)
        self.filehandler = filehandler.streamanalyser_filehandler
        self.collector = datacollector.DataCollector(
            sid, msglimit, verbose
        )
        self.refiner = datarefiner.DataRefiner(self.verbose)
        self.canalyser = None

        if disable_logs:
            self._disable_logs()

        self.logger.info("Session start ==================================")

        self.filehandler.create_cache_dir(self.sid)

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

    def clear_cache(self):
        self.filehandler.clear_cache()

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
        self.metadata = self.filehandler.read_metadata()
        
    def refine_data(self):
        """ Refines read data """
        self.messages = self.refiner.refine_raw_messages(
            self._raw_messages,
            self.msglimit
        )
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
        canalyser.analyse()
        self.highlights = canalyser.highlights

    def analyse(self):
        # TODO implement this logic
        #if not self.already_cached:
        self.collect_data()
        self.read_data()
        self.refine_data()
        self.analyse_data()

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
        
        # shuffle word list to minimize the issue where
        # repeating consecutive messages merge together
        # in the word cloud
        random.shuffle(wordlist)
        
        word_cloud = WordCloud(
            font_path = font_path,
            scale = scale
        ).generate(" ".join(wordlist))

        if self.verbose:
            print("Generating word cloud... done")
        return word_cloud

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
    
    #TODO Add output methods (graph, print etc.)
