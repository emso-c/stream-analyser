import loggersetup
import utils
from structures import (
    Message,
    Author
)


class Refiner():
    """ Refines raw data into a usable form """
    def __init__(self, msglimit=None, verbose=False):
        self.msglimit = msglimit
        self.verbose = verbose

        self.logger = loggersetup.create_logger(__file__)

    def refine_raw_messages(self, raw_messages) -> list[Message]:
        """ Refines raw messages and shapes them into Message dataclass """

        self.logger.info('Refining messages')
        messages = []
        if self.verbose:
            print(f"Refining messagess...0%", end='\r')
        try:
            for count, raw_message in enumerate(raw_messages):
                if self.msglimit and count == self.msglimit:
                    break
                if self.verbose:
                    print(f"Refining messages...{utils.percentage(count, self.msglimit if self.msglimit else len(raw_messages))}%", end='\r')
                messages.append(Message(
                    id=raw_message['message_id'],
                    text=raw_message['message'],
                    time=round(raw_message['time_in_seconds']),
                    author=Author(raw_message['author']['id'], raw_message['author']['name']))
                )
        except Exception as e:
            self.logger.error(e)
            raise Exception(e)
        finally:
            self.logger.debug(f"{len(messages)} messages has been found")
            if self.verbose:
                print(f"Reading messages... done")
            return messages