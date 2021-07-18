import urllib
import json
import requests

from chat_downloader import ChatDownloader

from .loggersetup import create_logger
from .utils import percentage

class DataCollector():
    """ A class that fetches required data to analyse the stream. """
    
    def __init__(self, id, msglimit=None, verbose=False) -> None:
        self.id = id
        self.msglimit = msglimit
        self.verbose = verbose

        self.metadata = {}
        self.logger = create_logger(__file__)
        self.iscomplete = False

    def collect_metadata(self) -> dict:
        """ Collects metadata of the YouTube stream """

        self.logger.info("Collecting metadata")
        if self.verbose:
            print(f"Collecting metadata...", end='\r')

        params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % self.id}
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
        try:
            with urllib.request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
        except Exception as e:
            self.logger.error(e)
            raise requests.HTTPError('Bad request: 400')
        if self.verbose:
            print(f"Collecting metadata... done")
        return data

    def fetch_raw_messages(self) -> list[dict]:
        """ Fetches live chat messages """

        self.logger.info("Fetching messages")
        raw_messages = []
        yt_url = "https://www.youtube.com/watch?v="+self.id
        corrupted_data_amount = 0
        try:
            for counter, raw_message in enumerate(ChatDownloader().get_chat(yt_url, start_time=0), start=1):
                if self.verbose:
                    print(f"Fetching raw messages... {str(percentage(counter, self.msglimit))+'%' if self.msglimit else counter}", end='\r')
                try:
                    # only fetch important fields
                    raw_messages.append({
                        "message_id":raw_message['message_id'],
                        "message":raw_message['message'],
                        "time_in_seconds":raw_message['time_in_seconds'],
                        "author":{"name":raw_message['author']['name'], "id":raw_message['author']['id']},
                    })
                except KeyError as e:
                    self.logger.warning(f"Corrupt message data skipped: {raw_message}")
                    corrupted_data_amount+=1
                    continue
                if self.msglimit and counter == self.msglimit:
                    break
        except Exception as e:
            self.logger.critical(f"Could not fetch messages: {e.__class__.__name__}:{e}")
            raise RuntimeError(f"Could not fetch messages: {e.__class__.__name__}:{e}")
        
        self.metadata['iscomplete'] = False
        if not self.msglimit:
            self.metadata['iscomplete'] = True

        if self.verbose:
            print(f"Fetching raw messages... done")

        self.logger.info(f'{len(raw_messages)-corrupted_data_amount} messages fetched ({corrupted_data_amount} corrupted)')
        return raw_messages

    def get_thumbnail_url(self, res_lvl=2) -> str:
        """ Gets URL of the thumbnail image.
        
        Args:
            res_lv (int, optional): Resolution level of the thumbnail. Defaults to 2.
                0 -> Medium res.
                1 -> High res.
                2 -> Standard res.
                3 -> Max res.

        Returns:
            str: URL of the thumbnail image.

        """
        self.logger.info("Getting thumbnail url")
        self.logger.debug(f"{res_lvl=}")

        res_lvls = ['mqdefault', 'hqdefault', 'sddefault', 'maxresdefault']
        
        if not 0 <= res_lvl < 4:
            self.logger.warning("res_lvl was out of range, set it to 2")
            res_lvl = 2

        return f'https://i.ytimg.com/vi/{self.id}/{res_lvls[res_lvl]}.jpg'