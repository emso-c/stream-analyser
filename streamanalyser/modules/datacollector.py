from os import stat
from typing import Tuple
from urllib import request, parse
import json

from yaml.events import DocumentStartEvent

from chat_downloader import ChatDownloader, errors
from chat_downloader.sites.youtube import YouTubeChatDownloader 
import isodate

from .structures import ImageResolution
from .loggersetup import create_logger
from .utils import percentage
from .exceptions import StreamIsLiveOrUpcomingError


class DataCollector:
    """A class that fetches required data to analyse the stream."""

    def __init__(self, id, log_path, msglimit=None, verbose=False, yt_api_key=None) -> None:
        self.id = id
        self.logger = create_logger(__file__, log_path, sid=id)
        if self._is_live_or_upcoming:
            raise StreamIsLiveOrUpcomingError("Stream needs to be archived first to get its messages")
        self._check_chat_replay()

        self.msglimit = msglimit
        self.verbose = verbose
        self.yt_api_key = yt_api_key

        self.iscomplete = False
        self.metadata = {}

    def _check_chat_replay(self):
        try:
            ChatDownloader().get_chat("https://www.youtube.com/watch?v=" + self.id, max_messages=1)
        except errors.NoChatReplay:
            self.logger.error(f"Chat replay is not available: https://www.youtube.com/watch?v={self.id}")
            raise errors.NoChatReplay("Chat replay is not available")

    def collect_metadata(self) -> dict:
        """Collects metadata of the YouTube stream"""

        self.logger.info("Collecting metadata")
        if self.verbose:
            print(f"Collecting metadata...", end="\r")

        data = self._get_oembed_respone()
        data['duration'] = self._get_video_duration()

        self.metadata = data
        if self.verbose:
            print(f"Collecting metadata... done")
        return data

    def _get_video_duration(self) -> int:
        if not self.yt_api_key:
            try:
                return int(YouTubeChatDownloader().get_video_data(self.id).get("duration"))
            except Exception as e:
                self.logger.error(f"Couldn't get video duration, returning -1 instead. ({e.__class__.__name__}: {e})")
                return -1
        return self._parse_duration(
            json.load(
                request.urlopen(
                    f"https://www.googleapis.com/youtube/v3/videos?id={self.id}&key={self.yt_api_key}&part=contentDetails"
                )
            )["items"][0]["contentDetails"]["duration"]
        )   

    @staticmethod
    def _parse_duration(yt_duration_response) -> int:
        return int(isodate.parse_duration(yt_duration_response).total_seconds())

    def _get_oembed_respone(self) -> dict:
        params = {
            "format": "json",
            "url": "https://www.youtube.com/watch?v=%s" % self.id,
        }
        url = "https://www.youtube.com/oembed"
        query_string = parse.urlencode(params)
        url = url + "?" + query_string
        try:
            with request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
        except request.URLError as e:
            self.logger.critical("Couldn't get oembed info. Returning empty metadata instead.")
            return {
                "title":"None",
                "author_name":"None",
                "author_url":"None",
                "type":"None",
                "height":-1,
                "width":-1,
                "version":"None",
                "provider_name":"None",
                "provider_url":"None",
                "thumbnail_height":-1,
                "thumbnail_width":-1,
                "thumbnail_url":"None",
                "html":"None"
            }
        except Exception as e:
            self.logger.error(e)
            raise e
        return data

    def _enforce_time_consistency(self, messages) -> Tuple[list, int]:
        """Quick fix for a bug where ChatDownloader module sometimes
        returns messages that are written LONG AFTER (~5 hours) the
        stream ends by removing the last message.
        """
        inconsistent_data_amount = 0
        if "duration" in self.metadata.keys():
            if not self.metadata["duration"]:
                self.logger.warning("Can't check time consistency as duration is not determined yet")
                return messages, 0
            while messages[-1]["time_in_seconds"] > self.metadata["duration"]:
                self.logger.warning(f"Deleted message as its time was exceeding the video length: {messages[-1]['time_in_seconds']} ({self.metadata['duration']})")
                inconsistent_data_amount+=1
                del messages[-1]
        return messages, inconsistent_data_amount

    @property
    def _is_live_or_upcoming(self) -> bool:
        """Returns if the stream is live or upcoming""" # lol
        return YouTubeChatDownloader().get_video_data(self.id).get("status") != 'past'

    def fetch_raw_messages(self) -> list[dict]:
        """Fetches live chat messages"""

        self.logger.info("Fetching messages")
        raw_messages = []
        yt_url = "https://www.youtube.com/watch?v=" + self.id
        corrupted_data_amount = 0
        try:
            for counter, raw_message in enumerate(
                ChatDownloader().get_chat(yt_url, start_time=0, message_groups=['messages', 'superchat']), start=1
            ):
                if self.verbose:
                    print(
                        f"Fetching raw messages... {str(percentage(counter, self.msglimit))+'%' if self.msglimit else counter}",
                        end="\r",
                    )
                try:
                    raw_messages.append(self._reformat_message(raw_message))
                except KeyError as e:
                    self.logger.warning(f"Corrupt message data skipped: {raw_message}")
                    corrupted_data_amount += 1
                    continue
                if self.msglimit and counter == self.msglimit:
                    break
        except Exception as e:
            print(e)
            self.logger.critical(
                f"Could not fetch messages: {e.__class__.__name__}:{e}"
            )
            raise e

        self.iscomplete = not bool(self.msglimit)
        raw_messages, inconsistent_data_amount = self._enforce_time_consistency(raw_messages)

        if self.verbose:
            print(f"Fetching raw messages... done")

        self.logger.info(
            f"{len(raw_messages)-corrupted_data_amount} messages fetched ({corrupted_data_amount} corrupted, {inconsistent_data_amount} inconsistent)"
        )

        return raw_messages

    @staticmethod
    def _reformat_message(message) -> dict:
        """Reformats messages returned from ChatDownloader."""
        reformatted_message = {
            "message_id": message["message_id"],
            "message_type": message["message_type"],
            "message": message["message"],
            "time_in_seconds": message["time_in_seconds"],
            "author": {
                "name": message["author"]["name"],
                "id": message["author"]["id"],
                "images": message["author"]["images"],
            }
        }
        if "emotes" in message.keys():
            reformatted_message["emotes"] = [{
                "id": emote["id"],
                "name": emote["name"],
                "images": emote["images"],
                "is_custom_emoji": emote["is_custom_emoji"]
            } for emote in message["emotes"]]
        if "badges" in message.get("author").keys():
            reformatted_message["author"]["badges"] = message["author"]["badges"]

        # Important: To get memberships and superchats, follow https://github.com/xenova/chat-downloader/pull/126/commits/14637d3f5a75fc97f480aa4f3732dde0134221ee
        if message.get("message_type") == "paid_message":
            reformatted_message["money"] = {
                "amount": message["money"]["amount"],
                "currency": message["money"]["currency"],
                "currency_symbol": message["money"]["currency_symbol"],
                "text": message["money"]["text"],
            }
            reformatted_message["colors"] = {
                "body_background_colour": message["body_background_colour"],
                "header_background_colour": message["header_background_colour"],
            }
        elif message.get("message_type") == "membership_item":
            reformatted_message["welcome_text"] = str(message["header_secondary_text"]),
        elif message.get("message_type") == "paid_sticker":
            reformatted_message["money"] = {
                "amount": message["money"]["amount"],
                "currency": message["money"]["currency"],
                "currency_symbol": message["money"]["currency_symbol"],
                "text": message["money"]["text"],
            }
            reformatted_message["colors"] = {
                "body_background_colour": message["background_colour"],
                "header_background_colour": None,
            }
            reformatted_message["sticker_images"] = message["sticker_images"]
        return reformatted_message
            
    def fetch_missing_messages(self, start_time, current_amount, target_amount=None) -> list[dict]:
        """Returns missing messages.

        Args:
            start_time (float): Starting time to fetch messages.
            current_amount (int): Current message amount.
            target_amount (int): Target message amount. Defaults to None,
                which returns all remaining messages.

        Returns:
            list[dict]: List of missing messages.
        """

        self.logger.info("Fetching missing messages")
        self.logger.debug(f"{start_time=}")
        self.logger.debug(f"{current_amount=}")
        self.logger.debug(f"{target_amount=}")

        yt_url = "https://www.youtube.com/watch?v=" + self.id
        corrupted_data_amount = 0
        raw_messages = []
        limit = current_amount + target_amount - 1 if target_amount else None

        for counter, raw_message in enumerate(
            ChatDownloader().get_chat(yt_url, start_time=start_time),
            start=current_amount,
        ):
            if self.verbose:
                print(
                    f"Fetching missing messages... {str(percentage(counter, limit))+'%' if target_amount else counter}",
                    end="\r",
                )
            try:
                raw_messages.append(self._reformat_message(raw_message))
            except KeyError:
                self.logger.warning(f"Corrupt message data skipped: {raw_message}")
                corrupted_data_amount += 1
                continue
            if target_amount and counter == limit:
                break

        if not self.iscomplete:
            self.iscomplete = not bool(target_amount)

        if self.verbose:
            print(f"Fetching missing messages... done")

        self.logger.info(
            f"{len(raw_messages)-corrupted_data_amount} messages fetched ({corrupted_data_amount} corrupted)"
        )

        return raw_messages

    def get_thumbnail_url(self, res_lvl:ImageResolution=ImageResolution.STANDARD) -> str:
        """Gets URL of the thumbnail image.

        Args:
            res_lv (ImageResolution, optional): Resolution level of the thumbnail. Defaults to `ImageResolution.STANDARD`.

        Returns:
            str: URL of the thumbnail image.

        """
        self.logger.info("Getting thumbnail url")
        self.logger.debug(f"{res_lvl=}")

        res_lvls = ["mqdefault", "hqdefault", "sddefault", "maxresdefault"]

        if not 0 <= res_lvl < 4:
            self.logger.warning("res_lvl was out of range, set it to 2")
            res_lvl = 2

        return f"https://i.ytimg.com/vi/{self.id}/{res_lvls[res_lvl]}.jpg"
