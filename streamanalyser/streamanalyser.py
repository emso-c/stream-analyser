import os
import traceback

from .modules import (
    chatanalyser,
    datacollector,
    loggersetup,
    filehandler,
    datarefiner,
    structures,
    utils
)

class StreamAnalyser():
    """[summary]
    """

    def __init__(self, sid, limit=None, verbose=False):
        self.sid = sid
        self.limit = limit
        self.verbose = verbose

        self.metadata = {}
        self._raw_messages = {}
        
        self.logger = loggersetup.create_logger(__file__, sid=sid)
        self.filehandler = filehandler.streamanalyser_filehandler
        self.collector = datacollector.DataCollector(
            self.sid, self.limit, self.verbose
        )

        self.filehandler.create_cache(self.sid)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)

    def _collect_data(self):
        """ Collects stream data using datacollector module """

        self.metadata = self.collector.collect_metadata()
        self._raw_messages = self.collector.fetch_raw_messages()

    def _cache_messages(self):
        self.filehandler.cache_messages(self._raw_messages)

    def _cache_metadata(self):
        self.filehandler.cache_metadata(self.metadata)
