from . import utils
from . import loggersetup
from .structures import Membership, Message, Author, Money, Superchat, SuperchatColor


class DataRefiner:
    """Refines raw data into a usable form"""

    def __init__(self, log_path=None, verbose=False):
        self.verbose = verbose

        self.messages = []
        self.authors = []
        self.logger = loggersetup.create_logger(__file__, log_path)

    def refine_raw_messages(self, raw_messages, msglimit=None) -> list[Message,Superchat,Membership]:
        """Refines raw messages and shapes them into Message dataclass"""

        self.logger.info("Refining messages")
        messages = []
        if self.verbose:
            print(f"Refining messagess...0%", end="\r")
        try:
            for count, raw_message in enumerate(raw_messages):
                if msglimit and count == msglimit:
                    break
                if self.verbose:
                    print(
                        f"Refining messages...{utils.percentage(count, msglimit if msglimit else len(raw_messages))}%",
                        end="\r",
                    )
                messages.append(
                    self._convert_message(raw_message)
                )
        except Exception as e:
            self.logger.error(f"{e.__class__.__name__}:{e}")
            raise Exception(f"{e.__class__.__name__}:{e}")
        finally:
            self.logger.debug(f"{len(messages)} messages has been refined")
            if self.verbose:
                print(f"Refining messages... done")
            self.messages = messages
            return messages

    def _convert_message(self, raw_message):
        """Converts raw message to data classes"""
        if raw_message.get("message_type") == "text_message":
            return Message(
                id=raw_message["message_id"],
                text=raw_message["message"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"]
                ),
            )
        elif raw_message.get("message_type") == "paid_message":
            return Superchat(
                id=raw_message["message_id"],
                text=raw_message["message"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"]
                ),
                money=Money(
                    amount=raw_message["money"]["amount"],
                    currency=raw_message["money"]["currency"],
                    currency_symbol=raw_message["money"]["currency_symbol"],
                    text=raw_message["money"]["text"],
                    color=SuperchatColor(
                        background=raw_message["colors"]["body_background_colour"],
                        header=raw_message["colors"]["header_background_colour"]
                    )
                ),
            )
        elif raw_message.get("message_type") == "membership_item":
            return Membership(
                id=raw_message["message_id"],
                text=raw_message["message"],
                membership_text=raw_message["membership_text"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"]
                ),
            )
        raise ValueError("Invalid message type")


    def get_authors(self) -> list[Author]:
        """Returns unique list of message authors"""

        if not self.messages:
            self.logger.warning("Please refine raw messages before getting authors")
            return []

        self.logger.info("Getting authors")
        authors = set()
        for count, message in enumerate(self.messages):
            if self.verbose:
                print(
                    f"Getting authors...{utils.percentage(count, len(self.messages))}%",
                    end="\r",
                )
            authors.add(message.author)

        if self.verbose:
            print(f"Getting authors... done")
        self.authors = list(authors)
        self.logger.debug(f"{len(self.authors)} authors has been found")
        return self.authors
