from os import stat
import urllib
import json

from chat_downloader import ChatDownloader, errors

from .loggersetup import create_logger
from .utils import percentage


class DataCollector:
    """A class that fetches required data to analyse the stream."""

    def __init__(self, id, log_path, msglimit=None, verbose=False) -> None:
        self.id = id
        self.msglimit = msglimit
        self.verbose = verbose

        self.logger = create_logger(__file__, log_path)
        self.iscomplete = False

    def collect_metadata(self) -> dict:
        """Collects metadata of the YouTube stream"""

        self.logger.info("Collecting metadata")
        if self.verbose:
            print(f"Collecting metadata...", end="\r")

        params = {
            "format": "json",
            "url": "https://www.youtube.com/watch?v=%s" % self.id,
        }
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
        try:
            with urllib.request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
        except Exception as e:
            self.logger.error(e)
            raise e
        if self.verbose:
            print(f"Collecting metadata... done")
        return data

    def fetch_raw_messages(self) -> list[dict]:
        """Fetches live chat messages"""

        self.logger.info("Fetching messages")
        raw_messages = []
        yt_url = "https://www.youtube.com/watch?v=" + self.id
        corrupted_data_amount = 0
        try:
            #TODO check if already live
            for counter, raw_message in enumerate(
                ChatDownloader().get_chat(yt_url, start_time=0), start=1
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

        if self.verbose:
            print(f"Fetching raw messages... done")

        self.logger.info(
            f"{len(raw_messages)-corrupted_data_amount} messages fetched ({corrupted_data_amount} corrupted)"
        )

        return raw_messages

    def _reformat_message(self, message) -> dict:
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
            

    def fetch_missing_messages(
        self, start_time, current_amount, target_amount=None
    ) -> list[dict]:
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

    def get_thumbnail_url(self, res_lvl=2) -> str:
        """Gets URL of the thumbnail image.

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

        res_lvls = ["mqdefault", "hqdefault", "sddefault", "maxresdefault"]

        if not 0 <= res_lvl < 4:
            self.logger.warning("res_lvl was out of range, set it to 2")
            res_lvl = 2

        return f"https://i.ytimg.com/vi/{self.id}/{res_lvls[res_lvl]}.jpg"
