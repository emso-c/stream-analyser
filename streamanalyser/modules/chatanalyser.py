from collections import Counter

import numpy as np
from colorama import Fore

from .loggersetup import create_logger
from . import utils
from .structures import(
    Intensity,
    Highlight
)
from .exceptions import (
    DifferentListSizeError,
    ConstantsNotAscendingError,
    ConstantsNotUniqueError
)

class ChatAnalyser:
    """ A class to analyse live chat messages """

    def __init__(self, refined_messages, stream_id='undefined', min_duration=5, window=30, threshold_constant=3, verbose = False):
        """
        Args:
            refined_messages (list[Message]): List of messages of the stream refined by
                the DataRefiner class.
            stream_id (str, optional): Stream id of the chat. Defaults to 'undefined'.
            min_duration (int): Minimum highlight duration (in seconds) to detect. Defaults to 5
            window (int, optional):  Time interval to calculate averages. Defaults to 30.
            threshold_constant(int, optional) The value that divides average highlight duration. Defaults to 3.
            verbose (bool, optional): [description]. Defaults to False.
        """
        self.messages = refined_messages
        self.stream_id = stream_id
        self.min_duration = min_duration
        self.window = window
        self.threshold_constant = threshold_constant
        self.verbose = verbose
        self.logger = create_logger(__file__)
        
        if not self.window > 1:
            self.logger.error('Interval must be bigger than one')
            raise ValueError('Interval must be bigger than one.')

        self.frequency = {}
        self.intensity_list = []
        self.fre_mov_avg = {}
        self.smooth_avg = []
        self.highlight_annotation = []
        self.highlights = []

    def get_frequency(self) -> dict:
        """ Creates frequency table of messages """

        self.logger.info("Calculating frequency")

        # create frequency table
        message_frequency = {}
        for i, message in enumerate(self.messages):
            if self.verbose:
                print(f"Calculating frequency...{round(utils.percentage(i, len(self.messages))/2)}%", end='\r')
            if message.time in message_frequency:
                message_frequency[message.time] += 1
            else:
                message_frequency[message.time] = 1

        # fill the blank seconds
        for sec in range(self.messages[-1].time):
            if self.verbose:
                print(f"Calculating frequency...{round(utils.percentage(sec, self.messages[-1].time)/2)+50}%", end='\r')
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
        """ Returns list of intensity which will be used for 
            measuring how tense was the highlight.

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

        if len(levels) != len(constants) != len(colors):
            self.logger.error('All lists should be the same size')
            raise DifferentListSizeError("All lists should be the same size")

        if constants != sorted(constants):
            self.logger.error('Constants should be in ascending order')
            raise ConstantsNotAscendingError("Constants should be in ascending order")

        if len(set(constants)) != len(constants):
            self.logger.error('All constants should be unique')
            raise ConstantsNotUniqueError("All constants should be unique")

        self.intensity_list = [
            Intensity(
                levels[i],
                constants[i],
                colors[i]
            ) for i in range(len(levels))]
        return self.intensity_list

    def calculate_moving_average(self) -> dict:
        """ Returns moving average of a table """

        self.logger.info("Calculating moving average")
        self.fre_mov_avg = {}
        stack = []  # holds frequency of the last {window} seconds
        for time, value in self.frequency.items():
            if self.verbose:
                print(f"Calculating moving average...{utils.percentage(time, len(self.frequency))}%", end='\r')
            if len(stack) == self.window:
                stack.pop(0)
            stack.append(value)
            self.fre_mov_avg[time] = sum(stack)/len(stack)

        if self.verbose:
            print(f"Calculating moving average... done")
        return self.fre_mov_avg

    def _smoothen(self, dict, w=40) -> list[np.ndarray]:
        return list(np.convolve(list(dict.values()), np.ones(w)/w, mode='same'))

    def smoothen_mov_avg(self) -> list[np.ndarray]:
        self.smooth_avg = self._smoothen(self.fre_mov_avg)
        return self.smooth_avg

    def create_highlight_annotation(self) -> list[int]:
        """ Creates highlight annotation from moving average.
            Values are either -1, 0 or 1 where 1 means it's increasing. """

        self.logger.info("Creating highlight annotation")
        self.highlight_annotation = []
        for i in range(len(self.smooth_avg)):
            if i == len(self.smooth_avg)-1:
                break
            if self.smooth_avg[i] < self.smooth_avg[i+1]:
                self.highlight_annotation.append(1)
            elif self.smooth_avg[i] > self.smooth_avg[i+1]:
                self.highlight_annotation.append(-1)
            else:
                self.highlight_annotation.append(0)
        self.logger.debug(f"{self.highlight_annotation=}")
        self.logger.debug(f"Total increasing duration: {self.highlight_annotation.count(1)}")
        self.logger.debug(f"Total decreasing duration: {self.highlight_annotation.count(-1)}")
        self.logger.debug(f"Total constant duration: {self.highlight_annotation.count(0)}")
        return self.highlight_annotation

    def line_colors(self) -> list[str]:
        """ Sets plot colors according to highlight annotation """

        self.logger.info("Setting line colors")

        colors = []
        for x in self.highlight_annotation:
            if x == 1:
                colors.append('g')
            elif x == -1:
                colors.append('r')
            else:
                colors.append('gray')
        return colors

    def detect_highlight_times(self) -> list[Highlight]:
        """ Detects highlight times and durations according to highlight annotation and 
            smoothened moving average.  Also sets frequency delta, which is the change 
            of frequency within highlight duration.

        Args:
            highlight_annotation (list[int]): Highlight annotation returned from
                create_highlight_annotation method.
            smooth_avg (list): Smoothened values of moving average of message frequency.
            min_duration (int): Minimum highlight duration to detect.
        Returns:
            list[Highlight]: List of highlight times
        """

        #TODO improve algorithm 
        self.logger.info("Detecting highlight times")

        self.highlights = []
        start_time = 0
        initial_frequency = 0
        for current_time in range(len(self.highlight_annotation)):
            if self.verbose:
                print(f"Detecting highlight timestamps... {utils.percentage(current_time, len(self.highlight_annotation))}%", end='\r')
            if not start_time and self.highlight_annotation[current_time] == 1:
                start_time = current_time
                initial_frequency = self.smooth_avg[current_time]

            if start_time and self.highlight_annotation[current_time] != 1:
                duration = current_time - start_time
                if duration < self.min_duration:
                    self.logger.debug(f"Highlight @{start_time} not added, duration was {duration}")
                    start_time = 0
                    continue
                delta = self.smooth_avg[current_time] - initial_frequency
                if delta < 0:
                    self.logger.debug(f"Highlight @{start_time} not added, delta was {delta}")
                    start_time = 0
                    continue
                self.highlights.append(Highlight(self.stream_id, start_time, duration, fdelta=delta))
                self.logger.debug(f"Highlight found: from {start_time} to {current_time} ({duration}s)")
                start_time = 0
        if self.verbose:
            print("Detecting highlight timestamps... done")
        return self.highlights

    def correct_highlights(self) -> list[Highlight]:
        """ Corrects highlights by removing highlights that are too short or filtered """

        # TODO consider highlight value 
        self.logger.info("Correcting highlights")
        
        if not self.highlights:
            return []

        avg_highlight_duration = sum([hl.duration for hl in self.highlights])/len(self.highlights)
        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(f"Correcting highlights... {utils.percentage(i, len(self.highlights))}", end='\r')
            if highlight.duration <= avg_highlight_duration/self.threshold_constant:
                self.highlights.remove(highlight)
                if self.verbose:
                    self.logger.debug(f"Removed highlight at {highlight.time}, duration was too short ({highlight.duration}s)")
        if self.verbose:
            print("Correcting highlights... done")
        return self.highlights

    def set_highlight_intensities(self)->list[Highlight]:
        """ Sets highlight intensities based on frequency delta """

        if not self.highlights:
            return []
        
        self.logger.info("Setting highlight intensities")
        avg_value = sum([hl.fdelta for hl in self.highlights])/len(self.highlights)
        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(f"Setting highlight intensities... {utils.percentage(i, len(highlights))}%", end='\r')
            for intensity in self.intensity_list:
                if highlight.fdelta > avg_value*intensity.constant:
                    highlight.intensity = intensity
            self.logger.debug(f"[{highlight.time}] => {highlight.intensity.level} ({highlight.fdelta})")
        if self.verbose:
            print("Setting highlight intensities... done")
        return self.highlights


    def get_highlight_messages(self) -> list[Highlight]:
        """ Gets messages typed during highlights """

        self.logger.info("Getting highlight messages")

        if not self.highlights:
            return []
        
        hl_idx = 0
        for message in self.messages:
            if self.verbose:
                print(f"Getting highlight messages... {utils.percentage(hl_idx, len(self.highlights))}%", end='\r')

            if self.highlights[hl_idx].time < message.time < self.highlights[hl_idx].duration+self.highlights[hl_idx].time:
                self.highlights[hl_idx].messages.append(message)

            if message.time >= self.highlights[hl_idx].duration+self.highlights[hl_idx].time:
                hl_idx+=1

            if hl_idx == len(self.highlights):
                break

        if self.verbose:
            print("Getting highlight messages... done")
        return self.highlights


    def get_highlight_keywords(self) -> list[Highlight]:
        """ Adds most frequently used words to the highlight list. """
        
        self.logger.info("Getting keywords")

        if not self.highlights:
            return []

        for i, highlight in enumerate(self.highlights):

            if self.verbose:
                print(f"Getting highlight keywords... {utils.percentage(i, len(self.highlights))}%", end='\r')
                
            words = []
            if highlight.messages:
                for message in highlight.messages:
                    #self.logger.debug(f"Splitting: {message.text}")
                    for word in list(set(message.text.split(' '))):
                        if utils.normalize(word):
                            #self.logger.debug(f"\t\t{word} normalised: {utils.normalize(word)}")
                            words.append(utils.normalize(word))
            
        
            for filter in self.keyword_filters:
                try:
                    while True:
                        #self.logger.debug(f"removed {filter} from keywords")
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
                self.logger.debug(f"No keyword found @{highlight.time}, removing highlight")
                self.highlights.remove(highlight)
            else:
                self.logger.debug(f"Keywords found @{highlight.time}: {highlight.keywords}")

        if self.verbose:
            print("Getting highlight keywords... done")
        return self.highlights


    def guess_context(self) -> list[Highlight]:
        """ Guesses context by looking up the keywords for each highlight. """

        self.logger.info("Guessing context")
        if not self.highlights:
            return

        with open(self.config['path-to']['contexts'], 'r', encoding='utf-8') as file:
            context_list = json.load(file)
            for i, highlight in enumerate(self.highlights):
                if self.verbose:
                    print(f"Guessing contexts... {utils.percentage(i, len(self.highlights))}%", end='\r')
                for keyword in highlight.keywords:
                    for context in context_list:
                        for trigger in context['triggers']:
                            if  (trigger["is_exact"] and trigger["phrase"] == keyword) or \
                                (not trigger["is_exact"] and trigger["phrase"] in keyword):
                                highlight.contexts.add(context['reaction_to'])
                if not highlight.contexts:
                    highlight.contexts = set(['None'])
                self.logger.debug(f"Guessed contexts @{highlight.time}: {highlight.contexts} from keywords {highlight.keywords}")
        if self.verbose:
            print(f"Guessing contexts... done")
        return self.highlights


    def get_highlights(self) -> list[Highlight]:
        """ Returns a filled highlight list. """

        self.detect_highlight_times()
        self.correct_highlights()
        self.set_highlight_intensities()
        self.get_highlight_messages()
        self.get_highlight_keywords()
        self.guess_context()
        return self.highlights
