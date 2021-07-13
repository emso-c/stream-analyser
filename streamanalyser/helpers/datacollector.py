import urllib
import json
import requests

from chat_downloader import ChatDownloader

import loggersetup
import utils

class DataCollector():
    """ A class that fetches required data to analyse the stream. """
    
    def __init__(self, id, msglimit=None, verbose=False) -> None:
        self.id = id
        self.msglimit = msglimit
        self.verbose = verbose

        self.metadata = None
        self.logger = loggersetup.create_logger(__file__)
        self.iscomplete = False

    def collect_metadata(self) -> dict:
        """ Collects metadata of the YouTube stream """

        if self.verbose:
            print(f"Collecting stream data...", end='\r')
        params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % self.id}
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
        try:
            with urllib.request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
                self.logger.info(f"{data=}")
        except Exception as e:
            self.logger.error(e)
            raise requests.HTTPError('Bad request: 400')
        if self.verbose:
            print(f"Collecting stream data... done")
        return data

    def fetch_raw_messages(self) -> list[dict]:
        """ Fetches live chat messages """

        self.logger.info("Caching messages")
        raw_messages = []
        try:
            for counter, raw_message in enumerate(ChatDownloader().get_chat(self._youtube_url, start_time=0), start=1):
                if self.verbose:
                    print(f"Fetching raw messages... {str(utils.percentage(counter, self.limit))+'%' if self.limit else counter}", end='\r')
                try:
                    raw_messages.append({
                            "message_id":raw_message['message_id'],
                            "message":raw_message['message'],
                            "time_in_seconds":raw_message['time_in_seconds'],
                            "author":{"name":raw_message['author']['name'], "id":raw_message['author']['id']},
                        })
                except KeyError as e:
                    self.logger.warning(f"Corrupt message data skipped: {raw_message}")
                    continue
                if self.limit and counter == self.limit:
                    break
        except Exception as e:
            self.logger.critical(f"Could not fetch messages: {e.__class__.__name__}:{e}")
            raise RuntimeError(f"Could not fetch messages: {e.__class__.__name__}:{e}")
        
        if not self.limit:
            self.iscomplete = True

        if self.verbose:
            print(f"Fetching raw messages... done")

        return raw_messages
