import os
import traceback

from .modules import (
    loggersetup,
    filehandler,
    datacollector,
    datarefiner,
    chatanalyser,
    structures,
    utils
)

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
        self.context_path = "..\\data\\context.json"
        
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

    def set_context_path(self, path):
        """ Sets a custom context path manually """
        self.context_path = path

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

    #TODO add other arguments
    def analyse_data(self):
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
        self.collect_data()
        self.cache_data()
        self.refine_data()
        self.analyse_data()