import os
import json
from collections import Counter
from typing import Optional
import string

from colorama import Fore
from matplotlib import collections, pyplot as plt, font_manager as fm, rcParams
import numpy as np

from .loggersetup import create_logger
from . import utils
from .structures import (
    Emote,
    Intensity,
    Highlight,
    ContextSourceManager,
    Context,
    Trigger
)
from .exceptions import (
    DifferentListSizeError,
    ConstantsNotAscendingError,
    ConstantsNotUniqueError,
    DuplicateContextException,
    UnexpectedException,
    ContextsAllCorruptException,
    PathAlreadyExistsException
)
from .keyphrase_finder import KeyphraseFinder

DEFAULT_FONT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "fonts", "NotoSansCJKjp-Bold.ttf"
)


class ChatAnalyser:
    """A class to analyse live chat messages

    Args:
        refined_messages (list[Message]): List of messages of the stream refined by
            the DataRefiner class.

        log_path(str): Path to log folder. Set to None to log without writing to a file.

        stream_id (str, optional): Stream id of the chat. Defaults to 'undefined'.

        min_duration (int): Minimum highlight duration (in seconds) to detect. Defaults to 5

        window (int, optional):  Time interval to calculate moving averages. Defaults to 30.

        threshold_constant(int, optional): The value that divides average highlight duration.
            Set higher to get shorter highlights. Defaults to 3.

        keyword_limit(int, optional): Keyword amount to retrieve. Defaults to 4.

        keyword_filters(list, optional): Keywords to filter. Defaults to [].

        default_context_path(str, optional): Path to the default context file. Defaults to
            DEFAULT_CONTEXT_SOURCE_PATH. Set to None to disable.

        verbose (bool, optional): Make the output verbose. Defaults to False.

        stop_words_path (bool, optional): Default stop word file (.txt) path to exclude in
            keyphrase collocations. Defaults to None.
    """

    def __init__(
        self,
        refined_messages,
        log_path,
        default_context_path,
        stream_id="undefined",
        min_duration=5,
        window=30,
        threshold_constant=3,
        keyword_limit=4,
        keyword_filters=[],
        verbose=False,
        stop_words_path = None
    ):
        self.messages = refined_messages
        self.stream_id = stream_id
        self.min_duration = min_duration
        self.window = window
        self.threshold_constant = threshold_constant
        self.keyword_limit = keyword_limit
        self.keyword_filters = keyword_filters
        self.default_context_path = default_context_path
        self.verbose = verbose
        self.stop_words_path = stop_words_path
        self.logger = create_logger(__file__, log_path)

        if not self.window > 1:
            self.logger.error("Interval must be bigger than one")
            raise ValueError("Interval must be bigger than one")

        self.frequency = {}
        self.intensity_list = []
        self.fre_mov_avg = {}
        self.exp_mov_avg = []
        self.highlight_annotation = []
        self.highlights = []

        self.contexts = list[Context]
        self.source = ContextSourceManager() # important
        if self.default_context_path:
            self.source.add(self.default_context_path)

    def read_contexts_from_sources(self) -> None:
        """Reads contexts from all sources and merges them into a list"""

        self.logger.info("Reading contexts")

        self.contexts = []
        for path in self.source.paths:
            with open(path, 'r', encoding='utf-8') as file:
                data = list(json.load(file))
                self.logger.debug(f"Read {len(data)} data from {path}")
                self.contexts.extend(data)

    def _check_contexts(self, autofix:bool=False) -> None:
        """Checks context compitability. Tries to autofix collisions if possible."""

        self.logger.info("Checking contexts")
        self.logger.debug(f"{autofix=}")
        
        # TODO check triggers too (right now it only checks reactions)
        seen_tuples = set()
        new_contexts = []
        for context in self.contexts:

            # Handle key error
            try:
                context["reaction_to"]
            except KeyError:
                if autofix:
                    continue # skip data
                else:
                    err_msg = f"Key 'reaction_to' not found in: {context}"
                    self.logger.error(err_msg)
                    raise KeyError(err_msg)

            # Handle duplicate data error
            reaction_tuple = tuple({'reaction_to', context.get('reaction_to')})
            if reaction_tuple not in seen_tuples:
                seen_tuples.add(reaction_tuple)
                new_contexts.append(context)
            else: 
                if autofix:
                    self.logger.warning(f"Merging duplicate context: {context['reaction_to']}")
                    i = next((i for i, nc in enumerate(new_contexts) if nc['reaction_to'] == context['reaction_to']), None)
                    if i == None:
                        self.logger.critical(f"Unexpected error: i={i}")
                        self.logger.critical(f"{new_contexts=}")
                        self.logger.critical(f"{context=}")
                        raise UnexpectedException("You should not be seeing this.")
                    new_contexts[i].get('triggers').extend(context.get('triggers'))
                else:
                    err_msg = f"Duplicate context, reaction to '{context.get('reaction_to')}' already exists"
                    self.logger.error(err_msg)
                    raise DuplicateContextException(
                        err_msg,
                        encounters=[] # TODO point at the source file/files
                    )
        self.contexts = new_contexts

    def parse_contexts(self, autofix:bool=False) -> list[Context]:
        """Parses the contexts from dictionary to dataclass format"""

        self.logger.info("Parsing contexts")

        parsed_contexts = []
        for context in self.contexts:
            try:
                parsed_contexts.append(
                    Context(
                        reaction_to=context['reaction_to'],
                        triggers=[
                            Trigger(
                                phrase=trigger['phrase'],
                                is_exact=trigger['is_exact']
                            ) for trigger in context['triggers']
                ]))
            except Exception as e:
                if autofix:
                    self.logger.warning(f"Skipping corrupt context data: {context}")
                    self.logger.warning(f"{e.__class__.__name__}: {e}")
                else:
                    self.logger.critical(f"Error parsing context: {context}")
                    self.logger.critical(f"{e.__class__.__name__}: {e}")
                    raise e

        if autofix and len(parsed_contexts) == 0 and len(self.contexts) != 0:
            self.logger.critical("Could not autofix, all contexts are corrupted")
            raise ContextsAllCorruptException(
                "Could not parse contexts, turn off autofix or check the log files to see the errors"
            )
        return parsed_contexts

    def get_contexts(self, autofix:bool=False) -> list[Context]:
        """Wrapper function to get the contexts"""
        self.read_contexts_from_sources()
        self._check_contexts(autofix=autofix)
        self.contexts = self.parse_contexts(autofix=autofix)
        return self.contexts

    def get_frequency(self) -> dict:
        """Creates frequency table of messages"""

        self.logger.info("Calculating frequency")

        # create frequency table
        message_frequency = {}
        for i, message in enumerate(self.messages):
            if self.verbose:
                print(
                    f"Calculating frequency...{round(utils.percentage(i, len(self.messages))/2)}%",
                    end="\r",
                )
            if message.time in message_frequency:
                message_frequency[message.time] += 1
            else:
                message_frequency[message.time] = 1

        # fill the blank seconds
        for sec in range(self.messages[-1].time):
            if self.verbose:
                print(
                    f"Calculating frequency...{round(utils.percentage(sec, self.messages[-1].time)/2)+50}%",
                    end="\r",
                )
            if not sec in message_frequency.keys():
                message_frequency[sec] = 0

        # sort
        self.frequency = {}
        for key in sorted(message_frequency.keys()):
            self.frequency[key] = message_frequency[key]
        if self.verbose:
            print(f"Calculating frequency... done")

        return self.frequency

    def init_intensity(self, levels=[], constants=[], colors=[]) -> list[Intensity]:
        """Returns list of intensity which will be used for
            measuring how tense was the highlight. Leave empty
            for default values.

        Args:
            levels (list): Names of the intensity levels.
            constants (list): Constants of the intensity levels.
            colors (list[AnsiFore]): Display colors of the intensity levels from colorama.

        Raises:
            DifferentListSizeError
            ConstantsNotAscendingError
            ConstantsNotUniqueError

        Returns:
            list[Intensity]: Intensity list
        """

        self.logger.info("Initializing intensity")
        self.logger.debug(f"{levels=}")
        self.logger.debug(f"{constants=}")
        self.logger.debug(f"{colors=}")

        levels = levels or ["medium", "high", "very high", "ultra high"]
        constants = constants or [0, 0.7, 1.4, 2.1]
        colors = colors or [Fore.YELLOW, Fore.BLUE, Fore.RED, Fore.MAGENTA]

        if len(levels) != len(constants) != len(colors):
            self.logger.error("All lists should be the same size")
            raise DifferentListSizeError("All lists should be the same size")

        if constants != sorted(constants):
            self.logger.error("Constants should be in ascending order")
            raise ConstantsNotAscendingError("Constants should be in ascending order")

        if len(set(constants)) != len(constants):
            self.logger.error("All constants should be unique")
            raise ConstantsNotUniqueError("All constants should be unique")

        self.intensity_list = [
            Intensity(levels[i], constants[i], colors[i]) for i in range(len(levels))
        ]
        return self.intensity_list

    def calculate_moving_average(self) -> dict:
        """Returns moving average of a table"""

        self.logger.info("Calculating moving average")
        self.fre_mov_avg = {}
        stack = []  # holds frequency of the last {window} seconds
        for time, value in self.frequency.items():
            if self.verbose:
                print(
                    f"Calculating moving average...{utils.percentage(time, len(self.frequency))}%",
                    end="\r",
                )
            if len(stack) == self.window:
                stack.pop(0)
            stack.append(value)
            self.fre_mov_avg[time] = sum(stack) / len(stack)

        if self.verbose:
            print(f"Calculating moving average... done")
        return self.fre_mov_avg

    def _smoothen(self, dict, w=40) -> list[np.ndarray]:
        return list(np.convolve(list(dict.values()), np.ones(w) / w, mode="same"))

    def smoothen_mov_avg(self) -> list[np.ndarray]:
        self.exp_mov_avg = self._smoothen(self.fre_mov_avg)
        return self.exp_mov_avg

    def create_highlight_annotation(self) -> list[int]:
        """Creates highlight annotation from moving average.
        Values are either -1, 0 or 1 where 1 means the value increasing."""

        self.logger.info("Creating highlight annotation")
        self.highlight_annotation = []
        for i in range(len(self.exp_mov_avg)):
            if i == len(self.exp_mov_avg) - 1:
                break
            if self.exp_mov_avg[i] < self.exp_mov_avg[i + 1]:
                self.highlight_annotation.append(1)
            elif self.exp_mov_avg[i] > self.exp_mov_avg[i + 1]:
                self.highlight_annotation.append(-1)
            else:
                self.highlight_annotation.append(0)

        for state, notation in {
            "increasing": 1,
            "decreasing": -1,
            "constant": 0,
        }.items():
            count = self.highlight_annotation.count(notation)
            self.logger.debug(f"Total {state} duration: {count}")

        return self.highlight_annotation

    def line_colors(self) -> list[str]:
        """Sets plot colors according to highlight annotation"""

        self.logger.info("Setting line colors")

        colors = []
        for x in self.highlight_annotation:
            if x == 1:
                colors.append("g")
            elif x == -1:
                colors.append("r")
            else:
                colors.append("gray")
        return colors

    def detect_highlight_times(self) -> list[Highlight]:
        """Detects highlight times and durations according to highlight annotation and
            smoothened moving average.  Also sets frequency delta, which is the change
            of frequency within highlight duration.

        Returns:
            list[Highlight]: List of highlight times
        """

        # TODO improve algorithm
        self.logger.info("Detecting highlight times")

        self.highlights = []
        start_time = 0
        initial_frequency = 0
        for current_time in range(len(self.highlight_annotation)):
            if self.verbose:
                print(
                    f"Detecting highlight timestamps... {utils.percentage(current_time, len(self.highlight_annotation))}%",
                    end="\r",
                )
            if not start_time and self.highlight_annotation[current_time] == 1:
                start_time = current_time
                initial_frequency = self.exp_mov_avg[current_time]

            if start_time and self.highlight_annotation[current_time] != 1:
                duration = current_time - start_time
                if duration < self.min_duration:
                    self.logger.debug(
                        f"Highlight @{start_time} was not added, duration was {duration}"
                    )
                    start_time = 0
                    continue
                delta = self.exp_mov_avg[current_time] - initial_frequency
                if delta < 0:
                    self.logger.debug(
                        f"Highlight @{start_time} was not added, delta was {delta}"
                    )
                    start_time = 0
                    continue
                self.highlights.append(
                    Highlight(self.stream_id, start_time, duration, fdelta=delta)
                )
                self.logger.debug(
                    f"Highlight found: from {start_time} to {current_time} ({duration}s)"
                )
                start_time = 0
        if self.verbose:
            print("Detecting highlight timestamps... done")
        return self.highlights

    def correct_highlights(self) -> list[Highlight]:
        """Corrects highlights by removing highlights that are too short or filtered"""

        # TODO consider fdelta too
        self.logger.info("Correcting highlights")

        if not self.highlights:
            return []

        if len(self.highlights) != 1:
            self.highlights.pop(0)

        avg_highlight_duration = sum([hl.duration for hl in self.highlights]) / len(
            self.highlights
        )
        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(
                    f"Correcting highlights... {utils.percentage(i, len(self.highlights))}",
                    end="\r",
                )
            if highlight.duration <= avg_highlight_duration / self.threshold_constant:
                self.highlights.remove(highlight)
                if self.verbose:
                    self.logger.debug(
                        f"Removed highlight at {highlight.time}, duration was too short ({highlight.duration}s)"
                    )
        if self.verbose:
            print("Correcting highlights... done")
        return self.highlights

    def set_highlight_intensities(self) -> list[Highlight]:
        """Sets highlight intensities based on frequency delta"""

        if not self.highlights:
            return []

        self.logger.info("Setting highlight intensities")
        avg_value = sum([hl.fdelta for hl in self.highlights]) / len(self.highlights)
        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(
                    f"Setting highlight intensities... {utils.percentage(i, len(self.highlights))}%",
                    end="\r",
                )
            for intensity in self.intensity_list:
                if highlight.fdelta > avg_value * intensity.constant:
                    highlight.intensity = intensity
            self.logger.debug(
                f"[{highlight.time}] => {highlight.intensity.level} ({highlight.fdelta})"
            )
        if self.verbose:
            print("Setting highlight intensities... done")
        return self.highlights

    def get_highlight_messages(self) -> list[Highlight]:
        """Gets messages typed during highlights"""

        self.logger.info("Getting highlight messages")

        if not self.highlights:
            return []

        hl_idx = 0
        for message in self.messages:
            if self.verbose:
                print(
                    f"Getting highlight messages... {utils.percentage(hl_idx, len(self.highlights))}%",
                    end="\r",
                )

            if (
                self.highlights[hl_idx].time
                < message.time
                < self.highlights[hl_idx].duration + self.highlights[hl_idx].time
            ):
                self.highlights[hl_idx].messages.append(message)

            if (
                message.time
                >= self.highlights[hl_idx].duration + self.highlights[hl_idx].time
            ):
                hl_idx += 1

            if hl_idx == len(self.highlights):
                break

        if self.verbose:
            print("Getting highlight messages... done")
        return self.highlights

    @staticmethod
    def get_keyword_emotes(highlight:Highlight) -> set[Emote]:
        emotes = set()
        for msg in highlight.messages:
            for emote in msg.emotes:
                if emote:
                    emotes.add(emote)
        return emotes

    def get_highlight_keywords(self) -> list[Highlight]:
        """Adds most frequently used words to the highlight list"""

        print("\nWarning: `get_highlight_keywords` is deprecated, use `get_highlight_keyphrases` instead\n")

        self.logger.info("Getting keywords (old function)")

        if not self.highlights:
            return []

        for i, highlight in enumerate(self.highlights):

            if self.verbose:
                print(
                    f"Getting highlight keywords... {utils.percentage(i, len(self.highlights))}%",
                    end="\r",
                )

            words = []
            if highlight.messages:
                for message in highlight.messages:
                    for word in list(set(message.text.split(" "))):
                        normalized = utils.normalize(word)
                        if normalized:
                            words.append(normalized)

            for filter in self.keyword_filters:
                try:
                    while True:
                        words.remove(filter)
                except:
                    pass
            for filter in self.keyword_filters:
                try:
                    while True:
                        words.remove(filter.upper())
                except:
                    pass

            for _word, count in Counter(words).most_common(self.keyword_limit):
                if _word and count > 1:
                    highlight.keywords.append(_word)

            if not highlight.keywords:
                self.logger.debug(
                    f"No keyword found @{highlight.time}, removing highlight"
                )
                self.highlights.remove(highlight)
            else:
                self.logger.debug(
                    f"Keywords found @{highlight.time}: {highlight.keywords}"
                )

        if self.verbose:
            print("Getting highlight keywords... done")
        return self.highlights

    def get_highlight_keyphrases(self) -> list[Highlight]:
        """Adds most frequently used phrases to the highlight list."""

        self.logger.info("Getting keyphrases")

        if not self.highlights:
            return []

        finder = KeyphraseFinder(
            chat = [],
            fix_phrases = [
                ("let 's", "let's"),
                ("ca n't", "can't"),
                ("do n't", "don't"),
                ("he 's", "he's"),
                ("they 're", "they're"),
                ("it 's", "it's"),
                ("it ’ s", "it’s"),
                ("i 'm", "i'm"),
                ("you 're", "you're"),
            ],
            punctuation_list = list(string.punctuation) + ["！","？"],
            stop_words_path = self.stop_words_path
        )

        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(
                    f"Getting highlight keyphrases... {utils.percentage(i, len(self.highlights))}%",
                    end="\r",
                )

            if not highlight.messages:
                return self.highlights

            finder.chat = highlight.messages
            ### TODO
            # pass arguments
            # implement keyphrase class
            keywords = [r[0] for r in [tup for tup in finder.ngram_keyphrase_analysis(
                max_keyphrase_amount=self.keyword_limit,
                min_keyphrase_amount=self.keyword_limit, # to achieve non-dynamic keyphrase amount 
            )]]

            if keywords:
                highlight.keywords = keywords
                self.logger.debug(
                    f"Keyphrases found @{highlight.time}: {highlight.keywords}"
                )
                highlight.kw_emotes = list(ChatAnalyser.get_keyword_emotes(highlight))
            else:
                self.highlights.remove(highlight)
                self.logger.debug(
                    f"No keyphrase found @{highlight.time}, removing highlight"
                )

        if self.verbose:
            print("Getting highlight keyphrases... done")
        return self.highlights
    
    def _is_keyword_emote(self, keyword):
        return keyword.startswith(':') and keyword.endswith(':')

    def guess_context(self) -> list[str]:
        """Guesses context by looking up the keywords for each highlight."""

        self.logger.info("Guessing context")
        if not self.highlights:
            return

        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(
                    f"Guessing contexts... {utils.percentage(i, len(self.highlights))}%",
                    end="\r",
                )
            for keyword in highlight.keywords:
                for context in self.contexts:
                    for trigger in context.triggers:
                        kw = keyword if self._is_keyword_emote(keyword) else keyword.lower()
                        if  (trigger.is_exact and trigger.phrase == kw) or \
                            (not trigger.is_exact and trigger.phrase in kw):
                                highlight.contexts.add(context.reaction_to)
            if not highlight.contexts:
                highlight.contexts = set(["None"])
            self.logger.debug(
                f"Guessed contexts @{highlight.time}: {highlight.contexts} from keywords"
            )

        if self.verbose:
            print(f"Guessing contexts... done")
        return self.highlights

    def get_highlights(self, autofix_context_collision:bool=False) -> list[Highlight]:
        """Returns a filled highlight list."""

        self.detect_highlight_times()
        self.correct_highlights()
        self.init_intensity()
        self.set_highlight_intensities()
        self.get_highlight_messages()
        self.get_highlight_keyphrases()
        self.get_contexts(autofix=autofix_context_collision)
        self.guess_context()
        return self.highlights

    def draw_graph(self, title=None) -> plt:
        """Draws a basic graph of the analysed data including:
        - Message frequency
        - Moving average of message frequency
        - Highlights
        """

        # TODO make a better looking graph

        self.logger.info("Drawing graph")
        if self.verbose:
            print(f"Drawing graph...", end="\r")

        # TODO background img
        # img = mpimg.imread(f"{self.config['path-to']['thumbnails']}\\{self.stream_id}.jpg")

        fig, ax = plt.subplots(2, constrained_layout=True)

        # fm.fontManager.addfont(DEFAULT_FONT_PATH)
        # rcParams['font.family'] = [fm.get_font(DEFAULT_FONT_PATH).family_name]
        fprop = fm.FontProperties(fname=DEFAULT_FONT_PATH)
        fig.suptitle(title, fontproperties=fprop, fontsize=16)

        xAxis = list(self.frequency)
        yAxis = self.exp_mov_avg
        lines = [
            ((x0, y0), (x1, y1))
            for x0, y0, x1, y1 in zip(xAxis[:-1], yAxis[:-1], xAxis[1:], yAxis[1:])
        ]
        colors = self.line_colors()
        colored_lines = collections.LineCollection(
            lines, colors=colors, linewidths=(2,)
        )
        ax[0].add_collection(colored_lines)
        ax[0].autoscale_view()
        ax[0].set_title("Highlights")

        yAxis = list(self.frequency.values())
        ax[1].bar(xAxis, yAxis)
        yAxis = list(self.fre_mov_avg.values())
        ax[1].plot(xAxis, yAxis, "m--")
        ax[1].set_title("Message frequency")

        if self.verbose:
            print(f"Drawing graph... done")

        self.fig = plt
        return plt

    def analyse(self, levels=None, constants=None, colors=None, autofix_context_collision:bool=False):
        self.get_frequency()
        self.calculate_moving_average()
        self.smoothen_mov_avg()
        self.create_highlight_annotation()
        self.detect_highlight_times()
        self.correct_highlights()
        self.init_intensity(levels, constants, colors)
        self.set_highlight_intensities()
        self.get_highlight_messages()
        self.get_highlight_keyphrases()
        self.get_contexts(autofix=autofix_context_collision)
        self.guess_context()
