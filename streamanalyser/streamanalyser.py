from collections import Counter
import os
import random
import traceback
from typing import Tuple

from wordcloud import WordCloud
import wordcloud

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
            self,
            sid,
            msglimit=None,
            disable_logs = False,
            verbose=False
        ):

        self.sid = sid
        self.msglimit = msglimit
        self.disable_logs = disable_logs
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

        #TODO don't log this
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

    def _cache_messages(self):
        self.filehandler.cache_messages(self._raw_messages)

    def _cache_metadata(self):
        self.filehandler.cache_metadata(self.metadata)

    def _cache_thumbnail(self):
        self.filehandler.cache_thumbnail(self._thumbnail_url)

    def collect_data(self, thumb_res_lvl=2):
        """ Collects stream data using datacollector module """
        self.metadata = self.collector.collect_metadata()
        self._raw_messages = self.collector.fetch_raw_messages()
        # TODO self.thumbreslvl
        self._thumbnail_url = self.collector.get_thumbnail_url(thumb_res_lvl)

    def cache_data(self):
        self._cache_metadata()
        self._cache_messages()
        self._cache_thumbnail()

    def refine_data(self):
        self.messages = self.refiner.refine_raw_messages(
            self._raw_messages,
            self.msglimit
        )
        self.authors = self.refiner.get_authors()

    def analyse_data(self):
        #TODO Add other arguments
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
        if not self.already_cached:
            self.collect_data()
            self.cache_data()
        self.refine_data()
        self.analyse_data()

    def generate_wordcloud(self, font_path=None, scale=3) -> WordCloud:
        """ Returns word cloud of the stream

        Args:
            font_path (str, optional): Custom font path. Defaults to None.
            scale (int, optional): Scale of the resulting wordcloud.
                Might want to decrease for more performance. Defaults to 3.
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

    
    
    #TODO Add output methods (graph, print etc.)
