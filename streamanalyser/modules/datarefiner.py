from . import utils
from . import loggersetup
from .structures import Emote, Icon, Membership, Message, Author, Money, Sticker, Superchat, SuperchatColor


class DataRefiner:
    """Refines raw data into a usable form"""

    def __init__(self, log_path=None, verbose=False):
        self.verbose = verbose

        self.messages = []
        self.authors = []
        self.logger = loggersetup.create_logger(__file__, log_path)

    def refine_raw_messages(self, raw_messages, msglimit=None) -> list[Message,Superchat,Membership]:
        """Refines raw messages and shapes them into Message dataclass.
            
            Also gets all unique authors. This behavior was separate as per single responsibility principle
            but now they're merged to improve performance. 
        """

        self.logger.info("Refining messages")
        messages = []
        authors = []
        skipped_message_amount = 0
        if self.verbose:
            print(f"Refining messagess...0%", end="\r")
        for count, raw_message in enumerate(raw_messages):
            if msglimit and count == msglimit:
                break
            if self.verbose:
                print(
                    f"Refining messages...{utils.percentage(count, msglimit if msglimit else len(raw_messages))}%",
                    end="\r",
                )
            try:
                convertedMessage = self._convert_message(raw_message)
                messages.append(convertedMessage)
                authors.append(convertedMessage.author)
            except ValueError as e:
                self.logger.warning(f"{e.__class__.__name__}: {e}")
                self.logger.debug(f"Corrupt message was {raw_message}")
                skipped_message_amount += 1
            except Exception as e:
                self.logger.error(f"{e.__class__.__name__}:{e}")
                skipped_message_amount += 1
        self.logger.debug(f"{len(messages)} messages has been refined ({skipped_message_amount} skipped)")
        self.logger.debug(f"{len(self.authors)} authors has been found")
        if self.verbose:
            print(f"Refining messages... done")
        self.messages = messages
        self.authors = list(dict.fromkeys(authors))
        return messages

    def _convert_message(self, raw_message):
        """Converts raw message to data classes"""

        text = raw_message["message"]
        if not text:
            text = ""
        emotes=[]
        if "emotes" in raw_message.keys():
            emotes=[Emote(
                id=emote["id"],
                name=emote["name"],
                is_custom_emoji=emote["is_custom_emoji"],
                images=[Icon(
                    id=img["id"] if emote["is_custom_emoji"] else "None",
                    url=img["url"],
                    height=img["height"] if "height" in img.keys() else 0,
                    width=img["width"] if "width" in img.keys() else 0,
                ) for img in emote["images"]],
            ) for emote in raw_message["emotes"]]

        is_member=False
        membership_info=""
        membership_icons=[]
        if "badges" in raw_message["author"].keys():
            if "icons" in raw_message["author"]["badges"][0].keys():
                membership_icons = [
                        Icon(
                            id=img["id"],
                            url=img["url"],
                            height=img["height"] if "height" in img.keys() else 0,
                            width=img["width"] if "width" in img.keys() else 0,
                        ) for img in raw_message["author"]["badges"][0]["icons"]]
            for badge in raw_message["author"]["badges"]:
                if "member" in badge["title"].lower():
                    is_member=True
                    membership_info=badge["title"]

        author=Author(
            id=raw_message["author"]["id"],
            name=raw_message["author"]["name"],
            is_member=is_member,
            membership_info=membership_info,
            images={
                "profile":[
                    Icon(
                        id=img["id"],
                        url=img["url"],
                        height=img["height"] if "height" in img.keys() else 0,
                        width=img["width"] if "width" in img.keys() else 0,
                    ) for img in raw_message["author"]["images"]
                ],
                "membership": membership_icons
            }
        )
        if raw_message.get("message_type") == "text_message":
            return Message(
                id=raw_message["message_id"],
                text=text,
                time=round(raw_message["time_in_seconds"]),
                author=author,
                emotes=emotes
            )
        elif raw_message.get("message_type") == "paid_message":
            return Superchat(
                id=raw_message["message_id"],
                text=text,
                time=round(raw_message["time_in_seconds"]),
                author=author,
                money=Money(
                    amount=raw_message["money"]["amount"],
                    currency=raw_message["money"]["currency"],
                    currency_symbol=raw_message["money"]["currency_symbol"],
                    text=raw_message["money"]["text"],
                ),
                colors=SuperchatColor(
                    background=raw_message["colors"]["body_background_colour"],
                    header=raw_message["colors"]["header_background_colour"]
                ),
                emotes=emotes
            )
        elif raw_message.get("message_type") == "membership_item":
            return Membership(
                id=raw_message["message_id"],
                text=text,
                welcome_text=raw_message["welcome_text"],
                time=round(raw_message["time_in_seconds"]),
                author=author,
                emotes=emotes
            )
        elif raw_message.get("message_type") == "paid_sticker":
            return Sticker(
                id=raw_message["message_id"],
                text=text,
                time=round(raw_message["time_in_seconds"]),
                author=author,
                money=Money(
                    amount=raw_message["money"]["amount"],
                    currency=raw_message["money"]["currency"],
                    currency_symbol=raw_message["money"]["currency_symbol"],
                    text=raw_message["money"]["text"],
                ),
                colors=SuperchatColor(
                    background=raw_message["colors"]["body_background_colour"],
                    header=raw_message["colors"]["header_background_colour"]
                ),
                emotes=emotes,
                sticker_images=raw_message["sticker_images"],
            )
        raise ValueError(f"Invalid message type: {raw_message.get('message_type')}")


    def get_authors(self) -> list[Author]:
        """Returns unique list of message authors"""

        if not self.authors:
            self.logger.warning("Raw messages should be refined before getting authors")
            return []

        return self.authors
