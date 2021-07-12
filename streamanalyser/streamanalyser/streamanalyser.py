# -*- coding: utf-8 -*-
import os
import json
import warnings
from time import time
from datetime import timedelta
from collections import Counter
from shutil import copyfile
from typing import Tuple
import requests
import urllib
import urllib.request

import yaml
import numpy as np
from chat_downloader import ChatDownloader
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.font_manager as fm
from matplotlib import collections
from colorama import init, Fore, Back, Style

from .utils import utils
from .utils import logger_setup
from .utils.structures import (
    Message,
    Highlight,
    Author,
    Intensity
)

class StreamAnalyser():
    #TODO docstrings
    def __init__(
            self,
            stream_id,
            limit=None,
            keyword_limit=None,
            window=30,
            res_lvl=2,
            clear_cache=False,
            ignore_warnings=False,
            enforce_integrity=False,
            verbose=False
        ):
        """
        Args:
            stream_id (str): Id of the YouTube live stream URL.

            limit (int, optional): Amount of messages to fetch. Defaults to None.

            keyword_limit (int, optional): Keyword amount to retrieve. Defaults to None,
                which sets keyword limit from the config file.

            intensity_filter (list[str], optional): The names of intensity levels to filter out. Defaults to [].
                Default filter names can be found and modified in the config file.

            window (int, optional): Window size to calculate moving average. Defaults to 30.

            res_lvl (int, optional): Resolution level for the thumbnail. Defaults to 2.
                Resolution levels are sorted by quality, 0 being lowest and 3 being highest.

            clear_cache (bool, optional): Recreate the JSON file before getting messages. Defaults to False.
                Note that turning this option on each time would significantly slow down the
                process if the data will be used more than once.
            
            ignore_warnings (bool, optional): Ignore warnings. Defaults to False.

            enforce_integrity (bool, optional): Enforces file integrity by clearing 
                caches of id's with missing files. Use with caution. Defaults to False.

            verbose (bool, optional): Whether the functions should be verbose or not. Defaults to False.
        """
        init() # for colorama

        path = os.path.abspath(__file__).split('\streamanalyser.py')[0]
        self.config = yaml.load(open(f"{path}\\config.yaml", 'r'), Loader=yaml.Loader)
        for fname in self.config['path-to']:
            if fname == "default-export":
                continue
            self.config['path-to'][fname] = f"{path}\\{self.config['path-to'][fname]}"

        # delete dummy files
        for fname in ['cache','logs','metadata','thumbnails','fonts']:
            utils.delete_file_if_exists(f"{self.config['path-to'][fname]}\\delete.this")

        # logging configuration
        utils.delete_old_files(
            self.config['path-to']['logs'],
            self.config['log-duration-days']
        )
        self.logger = logger_setup.create_logger(
            name=__file__,
            sid=stream_id,
            logpath=self.config['path-to']['logs']+'\\'+ utils.get_logname()
        )
        self.logger.setLevel(10)

        self.logger.info('=============================================================')
        self.logger.info('===================== Session start =========================')
        self.logger.info('=============================================================')
        
        if enforce_integrity:
            self.enforce_file_integrity()
        else:
            self.check_file_integrity()
        
        try:
            self.metadata = yaml.load(open(f"{self.config['path-to']['metadata']}\\{stream_id}.yaml", 'r'), Loader=yaml.Loader)
        except FileNotFoundError:
            self.logger.debug('Metadata file not found when initializing the object')

        self.stream_id = stream_id
        self.limit = limit
        if self.limit:
            self.limit = round(self.limit)
        self.keyword_limit = keyword_limit if keyword_limit else self.config['keyword-limit']
        self.keyword_filters = self.config['keyword-filters']
        self.window = window
        self.clear_cache = clear_cache
        self.ignore_warnings = ignore_warnings
        self.verbose = verbose

        self.__youtube_url = f'https://www.youtube.com/watch?v={stream_id}'
        self.info = self.collect_stream_info()
        self.thumbnail_url = self.set_thumbnail_url(res_lvl)
        self.download_thumbnail()
        self.title = self.info['title']
        self.author = self.info['author_name']

        self.messages = [] #list[Message]
        self.authors = [] #list[Author]
        self.message_frequency = {} #dict
        self.fre_mov_avg = {} #dict
        self.smooth_avg = [] #list
        self.intensity_list = [] #list[Intensity]
        self.highlight_annotation = [] #list[int]
        self.highlights = [] #list[Highlight]
        self.fig = [] #list[plt.Line2D]


    def collect_stream_info(self) -> dict:
        """ Collects info of the stream such as title and author """

        if self.verbose:
            print(f"Collecting stream data...", end='\r')
        params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % self.stream_id}
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
        data = {}
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


    def cache_messages(self):
        """ Stores live chat messages of a YouTube stream for a faster access to data. """

        self.logger.info("Caching messages")

        utils.delete_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json.gz")
        raw_messages = []
        try:
            for counter, raw_message in enumerate(ChatDownloader().get_chat(self.__youtube_url, start_time=0), start=1):
                if self.verbose:
                    print(f"Writing messages to {self.stream_id}.json...{str(utils.percentage(counter, self.limit))+'%' if self.limit else counter}", end='\r')
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

        try:
            with open(f"{self.config['path-to']['cache']}/{self.stream_id}.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(raw_messages, ensure_ascii=False, indent=4))
        except Exception as e:
            utils.delete_file(f"{self.config['path-to']['cache']}/{self.stream_id}.json")       
            self.logger.critical(f"Could not cache messages: {e.__class__.__name__}:{e}")
            raise RuntimeError(f"Could not cache messages: {e.__class__.__name__}:{e}")

        
        try:
            with open(f"{self.config['path-to']['metadata']}\\{self.stream_id}.yaml", 'w+') as file:
                yaml.dump({'is-complete': False if self.limit else True}, file, Dumper=yaml.Dumper)
                self.logger.info(f'Set is-complete to {False if self.limit else True}')
        except Exception as e:
            self.logger.error(f"Could not create metadata: {e}")
        self.metadata = yaml.load(open(f"{self.config['path-to']['metadata']}\\{self.stream_id}.yaml", 'r'), Loader=yaml.Loader)

        utils.compress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
        if self.verbose:
            print(f"Writing messages to {self.stream_id}.json... done")


    def get_messages_from_json(self) -> list[Message]:
        """ Gets messages from a JSON file and converts them into the Message object. """

        utils.decompress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
        try:
            self.logger.info('Reading messages')
            messages = []
            if self.verbose:
                print(f"Reading messages from {self.stream_id}.json...0%", end='\r')
            with open(f"{self.config['path-to']['cache']}/{self.stream_id}.json", encoding="utf8") as json_file:
                raw_messages = json.load(json_file)
                for count, raw_message in enumerate(raw_messages):
                    if self.limit and count == self.limit:
                        break
                    if self.verbose:
                        print(f"Reading messages from {self.stream_id}.json...{utils.percentage(count, self.limit if self.limit else len(raw_messages))}%", end='\r')
                    messages.append(Message(
                        id=raw_message['message_id'],
                        text=raw_message['message'],
                        time=round(raw_message['time_in_seconds']),
                        author=Author(raw_message['author']['id'], raw_message['author']['name']))
                    )
            
            self.logger.debug(f"{len(messages)} messages has been found")
        except Exception as e:
            self.logger.error(e)
        finally:
            utils.compress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
            if self.verbose:
                print(f"Reading messages from {self.stream_id}.json... done")
            self.messages = messages
            return self.messages


    def get_messages(self) -> get_messages_from_json:
        """ Helper function that calls cache_messages() -if there's no messages-
            and get_messages_from_json() consecutively in one call.
            
            Optimized to add new messages to the end of the JSON file if more messages then there is requested,
            rather than fetching every message from the start each time. For example if 1000 messages had been fetched before,
            and the user is requesting 1200 messages now, it would only fetch the last 200 messages instead of starting 
            all over again.

            Also checks if there are large amount of cached files and asks permission to delete the the least
            recently used one.

            DO NOT CLOSE THE PROGRAM DURING THE PROCESS
        """            
        
        if self.clear_cache or not os.path.isfile(f"{self.config['path-to']['cache']}/{self.stream_id}.json.gz"):
            if self.verbose:
                print(f'creating {self.stream_id}.json')
            self.logger.debug(f"Clearing cache. Reason: {'forced' if self.clear_cache else 'couldnt find cache file'}")
            self.cache_messages()
        else:
            if self.verbose:
                print(f'{self.stream_id}.json has been found.')
            utils.decompress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
            self.metadata = yaml.load(open(f"{self.config['path-to']['metadata']}\\{self.stream_id}.yaml", 'r'), Loader=yaml.Loader)
            with open(f"{self.config['path-to']['cache']}/{self.stream_id}.json", 'r+', encoding='utf-8') as file:
                if self.verbose:
                    print(f"Checking {self.stream_id}.json...", end='\r')
                data = file.read()
                file.seek(0)
                if len(data) == 0:
                    message_data = []
                    latest_message_time = 0
                else:
                    message_data = json.loads(data)
                    latest_message_time = message_data[-1]['time_in_seconds']
                if self.verbose:
                    print(f"Checking {self.stream_id}.json... done")
                self.logger.info('Checked messages')

                if self.limit and len(message_data) < self.limit:
                    if self.verbose:
                        print(f'Missing messages detected in {self.stream_id}.json ({self.limit-len(message_data)} messages)')
                    self.logger.warning("Missing messages detected")
                    for counter, raw_message in enumerate(ChatDownloader().get_chat(self.__youtube_url, start_time=latest_message_time), start=len(message_data)):
                        if counter == self.limit:
                            break
                        if self.verbose:
                            print(f"Writing messages to {self.stream_id}.json ({counter} messages)...", end='\r')
                        message_data.append(raw_message)
                    file.write(json.dumps(message_data, ensure_ascii=False, indent=4))
                    file.truncate()
                    if self.verbose:
                        print(f"Writing messages to {self.stream_id}.json ({len(message_data)} messages)... done")
                    self.logger.info(f"Written {self.limit-len(message_data)} messages")
                    
                elif not self.limit and (not 'is-complete' in self.metadata.keys() or not self.metadata['is-complete']):
                    # All messages has not been fetched before and now are being requested now.
                    # Since the real amount of all messages is not known, the only option is to clear cache.
                    if self.verbose:
                        print('Message cache has not been fully filled before. Fetching all the messages.')
                    self.logger.warning('Message cache has not been fully filled before. Fetching all the messages.')
                    self.cache_messages()
                    pass
            utils.compress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
        # delete the least recently used cache file if there are large amount of files
        file_amount = utils.file_amount(self.config['path-to']['cache'])
        if file_amount > self.config['cache-size']:
            self.logger.warning('Cache limit reached')
            self.logger.debug(f'{file_amount=}')
            self.logger.debug(f"{self.config['cache-size']=}")
            self.logger.debug(f'{self.least_recently_used_id=}')
            print(f"""
            WARNING: There are too many cached files in '{self.config['path-to']['cache']}'
            (You can either delete a file yourself or increase the cache size in config.yaml if you want)
            The least recently used file ({self.least_recently_used_id}.json) is going to be deleted.""")
            self.__clear_cache(self.least_recently_used_id)

        return self.get_messages_from_json()


    def get_authors(self) -> list[Author]:
        """ Returns unique list of message authors """

        self.logger.info("Getting authors")
        authors = set()
        for count, message in enumerate(self.messages):
            if self.verbose:
                print(f"Getting authors...{utils.percentage(count, len(self.messages))}%", end='\r')
            authors.add(message.author)
        
        if self.verbose:
            print(f"Getting authors... done")
        self.authors = list(authors)
        self.logger.debug(f"{len(self.authors)} authors has been found")
        return self.authors


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
        sorted_message_frequency = {}
        for key in sorted(message_frequency.keys()):
            sorted_message_frequency[key] = message_frequency[key]
        
        if self.verbose:
            print(f"Calculating frequency... done")
        self.message_frequency = sorted_message_frequency
        self.logger.info(f"{self.message_frequency=}")
        return self.message_frequency


    def init_intensity(self, levels=[], constants=[], colors=[]) -> list[Intensity]:
        """ Returns list of intensity which will be used for 
            measuring how tense was the highlight.

            In case of an error, tries to return the default intensity list.

        Args:
            levels (list): Names of the intensity levels.
            constants (list): Constants of the intensity levels.
            colors (list[AnsiFore]): Display colors of the intensity levels from colorama.

        Returns:
            list[Intensity]: Intensity list
        """

        self.logger.info("Initializing intensity")
        self.logger.debug(f"{levels=}")
        self.logger.debug(f"{constants=}")
        self.logger.debug(f"{colors=}")

        if len(levels) != len(constants) != len(colors):
            self.logger.error('All lists should be the same size')
            if not self.ignore_warnings:
                warnings.warn('All lists should be the same size', stacklevel=3)
            return self.config['intensity']

        if not levels:
            levels = self.config['intensity']['levels']
        if not constants:
            constants = self.config['intensity']['constants']
        if not colors:
            for color in self.config['intensity']['colors']:
                if color == "YELLOW":
                    colors.append(Fore.YELLOW)
                if color == "BLUE":
                    colors.append(Fore.BLUE)
                if color == "RED":
                    colors.append(Fore.RED)
                if color == "MAGENTA":
                    colors.append(Fore.MAGENTA)
                if color == "BLACK":
                    colors.append(Fore.BLACK)
                if color == "WHITE":
                    colors.append(Fore.WHITE)
                if color == "GREEN":
                    colors.append(Fore.GREEN)
                if color == "CYAN":
                    colors.append(Fore.CYAN)
        if constants != sorted(constants):
            self.logger.error('Constants should be in ascending order')
            if not self.ignore_warnings:
                warnings.warn('Constants should be in ascending order', stacklevel=3)
            return self.config['intensity']
        if len(set(constants)) != len(constants):
            self.logger.error('All constants should be unique')
            if not self.ignore_warnings:
                warnings.warn('All constants should be unique', stacklevel=3)
            return self.config['intensity']

        self.intensity_list = [Intensity(levels[i], constants[i], colors[i]) for i in range(len(levels))]
        return self.intensity_list


    def calculate_moving_average(self, table) -> dict:
        """ Returns moving average of a table
    
        Args:
            table (dict): The table to calculate averages. e.g. message frequency.

        Returns:
            dict: Moving average values of the table.
        """

        self.logger.info("Calculating moving average")
        self.logger.debug(f'{table=}')

        if not self.window > 1:
            self.logger.error('Interval must be bigger than one')
            raise ValueError('Interval must be bigger than one.')

        stack = []  # holds frequency for the last {window} seconds
        mov_avg = {}
        for time, value in table.items():
            if self.verbose:
                print(f"Calculating moving average...{utils.percentage(time, len(table))}%", end='\r')
            if len(stack) == self.window:
                stack.pop(0)
            stack.append(value)
            mov_avg[time] = sum(stack)/len(stack)
        self.logger.debug(f'{mov_avg=}')

        if self.verbose:
            print(f"Calculating moving average... done")

        return mov_avg


    def __smoothen(self, mov_avg, w=40) -> list:
        return list(np.convolve(list(mov_avg.values()), np.ones(w)/w, mode='same'))


    def create_highlight_annotation(self) -> list[int]:
        """ Creates highlight annotation from moving average.
            Values are either -1, 0 or 1 where 1 means it's a highlight. """

        self.logger.info("Creating highlight annotation")
        highlight_annotation = []
        for i in range(len(self.smooth_avg)):
            if i == len(self.smooth_avg)-1:
                break
            if self.smooth_avg[i] < self.smooth_avg[i+1]:
                highlight_annotation.append(1)
            elif self.smooth_avg[i] > self.smooth_avg[i+1]:
                highlight_annotation.append(-1)
            else:
                highlight_annotation.append(0)
        self.logger.debug(f"{highlight_annotation=}")
        self.logger.debug(f"Total increasing duration: {highlight_annotation.count(1)}")
        self.logger.debug(f"Total decreasing duration: {highlight_annotation.count(-1)}")
        self.logger.debug(f"Total constant duration: {highlight_annotation.count(0)}")
        self.highlight_annotation = highlight_annotation
        return self.highlight_annotation


    def line_colors(self, highlight_annotation) -> list[str]:
        """ Sets plot colors according to highlight annotation """

        self.logger.info("Setting line colors")

        colors = []
        for x in highlight_annotation:
            if x == 1:
                colors.append('g')
            elif x == -1:
                colors.append('r')
            else:
                colors.append('gray')
        return colors


    def detect_highlight_times(self) -> list[Highlight]:
        """ Detects highlight times and durations according to highlight annotation and smoothened average. 
            Also sets frequency delta, which is the change of frequency within highlight duration. """
        #TODO improve algorithm 
        self.logger.info("Detecting highlight times")

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
                if duration < self.config['min-hl-duration']:
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
        """ Corrects highlights by removing highlights that are too short or filtered. """

        # TODO consider highlight value 
        self.logger.info("Correcting highlights")
        
        if not self.highlights:
            return []

        avg_highlight_duration = sum([hl.duration for hl in self.highlights])/len(self.highlights)
        for i, highlight in enumerate(self.highlights):
            if self.verbose:
                print(f"Correcting highlights... {utils.percentage(i, len(self.highlights))}", end='\r')
            if highlight.duration <= avg_highlight_duration/3:
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
                print(f"Setting highlight intensities... {utils.percentage(i, len(self.highlights))}%", end='\r')
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


    def draw_graph(self) -> plt:
        """ Draw graph of the analysed data
            - Message frequency   
            - Moving average of message frequency   
            - Highlights
        """

        #TODO make a better looking graph

        self.logger.info("Drawing graph")
        if self.verbose:
            print(f"Drawing graph...", end='\r')

        #TODO background img
        img = mpimg.imread(f"{self.config['path-to']['thumbnails']}\\{self.stream_id}.jpg")

        fig, ax = plt.subplots(2, constrained_layout = True)

        if os.path.exists(f"{self.config['path-to']['fonts']}\\NotoSansCJKjp-regular.otf"):
            fprop = fm.FontProperties(fname=f"{self.config['path-to']['fonts']}\\NotoSansCJKjp-regular.otf")
        else:    
            fprop = None
            warn_msg = f"If you want to see titles in Japanese font, \
please download the font from https://www.google.com/get/noto/#sans-jpan \
and put the 'NotoSansCJKjp-regular.otf' file into {self.config['path-to']['fonts']}"
            if not self.ignore_warnings:
                warnings.warn(warn_msg, stacklevel=3)
            self.logger.warning(warn_msg)

        fig.suptitle(self.title, fontproperties=fprop, fontsize=16)
        
        xAxis = list(self.message_frequency)
        yAxis = self.smooth_avg
        lines = [((x0,y0), (x1,y1)) for x0, y0, x1, y1 in zip(xAxis[:-1], yAxis[:-1], xAxis[1:], yAxis[1:])]
        colors = self.line_colors(self.highlight_annotation)
        colored_lines = collections.LineCollection(lines, colors=colors, linewidths=(2,))
        ax[0].add_collection(colored_lines)
        ax[0].autoscale_view()
        ax[0].set_title('Highlights')

        yAxis = list(self.message_frequency.values())
        ax[1].bar(xAxis, yAxis)
        yAxis = list(self.fre_mov_avg.values())
        ax[1].plot(xAxis, yAxis, 'm--')
        ax[1].set_title('Message frequency')
        
        if self.verbose:
            print(f"Drawing graph... done")
        
        self.fig = plt
        return plt


    def export_data(self, path=None, folder_name=None):
        """ Exports the analysed data to the path.

        Args:
            path (str|None, optional): Path to export the results. Defaults to None,
                which exports data to the default path.
            folder_name (str|None, optional): File name to export the results. Defaults to None,
                which exports data under the file named current UNIX timestamp.

        """

        self.logger.info("Exporting data")
        self.logger.debug(f"{path=}")
        self.logger.debug(f"{folder_name=}")

        if not path:
            path = self.config['path-to']['default-export']
        
        try:
            utils.create_dir_if_not_exists(path)
        except PermissionError:
            return
        
        if not folder_name:
            folder_name = str(int(time()))
        else:
            for name in os.listdir(path):
                if os.path.isdir(os.path.join(path, name)) and name == folder_name:
                    folder_name = folder_name+'_'+str(int(time()))
                    warn_msg = f"{name} already exists, renaming to {folder_name}"
                    if not self.ignore_warnings:
                        warnings.warn(warn_msg, stacklevel=3)
                    self.logger.warning(warn_msg)
                    break
                    
        target_path = path+'\\'+folder_name
        utils.create_dir_if_not_exists(target_path)
        
        if self.verbose:
            print(f"Exporting data to {target_path}...", end='\r')

        utils.decompress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
        copyfile(src=rf"{self.config['path-to']['cache']}/{self.stream_id}.json", dst=rf'{target_path}/messages.json')
        utils.compress_file(f"{self.config['path-to']['cache']}\\{self.stream_id}.json")
        self.logger.info("Exported messages")

        copyfile(src=rf"{self.config['path-to']['metadata']}/{self.stream_id}.yaml", dst=rf'{target_path}/metadata.yaml')
        self.logger.info("Exported metadata")

        copyfile(src=rf"{self.config['path-to']['thumbnails']}/{self.stream_id}.jpg", dst=rf'{target_path}/thumbnail.jpg')
        self.logger.info("Exported thumbnail")

        if self.highlights:
            with open(rf'{target_path}/highlights.txt', 'w', encoding='utf-8') as file:
                file.writelines([hl.colorless_str+'\n' for hl in self.highlights])
            self.logger.info("Exported highlights")
            
        if self.fig:
            self.fig.savefig(rf'{target_path}/graph.png')
            self.logger.info("Exported graph")


        if self.verbose:    
            print(f"Exporting data to {target_path}... done")
        
        try:
            os.startfile(target_path)
            self.logger.info(f"Opened {target_path} in file explorer")
        except FileNotFoundError:
            print("Couldn't find the file.")
            self.logger.error(f"Couldn't find {target_path}")


    def analyse(self):
        """ All in one function for analysing the chat
            Gets default values from the config file. """

        self.get_messages()
        self.get_authors()
        self.get_frequency()
        self.fre_mov_avg = self.calculate_moving_average(self.message_frequency)
        self.smooth_avg = self.__smoothen(self.fre_mov_avg)
        self.create_highlight_annotation()
        self.init_intensity()
        self.get_highlights()
        self.draw_graph()


    def print_summary(self, top=None, intensity_filters=[]) -> list[Highlight]:
        """ Only prints time and intensity of the highlights.

        Args:
            top (int, optional): Top n highlights to print, sorted by intensity. Defaults to None, which returns all.
            intensity_filters (list[str]): Intensity levels to filter out. Defaults to [].

        Returns:
            list[Highlight]: list of printed highlights
        """
        
        self.logger.info("Printing summary")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        highlights_to_return = []
        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Summary:"+Style.RESET_ALL)
        for _count, highlight in enumerate(highlights):
            if not highlight.intensity in intensity_filters:
                print(f'{timedelta(seconds=int(highlight.time))}: {highlight.intensity.colored_level}')
                highlights_to_return.append(highlight)
                self.logger.debug(highlight.colorless_str)

                if top and _count == top:
                    return highlights_to_return

        return highlights_to_return


    def print_highlights(self, top=None, include=[], not_include=[], intensity_filters=[]) -> list[Highlight]:
        """ Prints filtered or unfiltered highlights.

        Args:
            top (int, optional): Top n highlights to print, sorted by intensity. Defaults to None, which returns all.
            include (list[str], optional): List of reactions to see. Defaults to [].
                Reaction names can be found in context.json.
            not_include (list[str], optional): List of reactions to not see, overrides include. Defaults to [].
                Reaction names can be found in context.json.
            intensity_filters (list[str]): Intensity levels to filter out. Defaults to [].

        Returns:
            list[Highlight]: List of printed highlights

        """

        self.logger.info("Printing highlights")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        _count = 0
        highlights_to_return = []
        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Highlights:"+Style.RESET_ALL)
        for highlight in highlights:
            skip = False
            for context in highlight.contexts:
                if not_include and context in not_include:
                    skip = True
                    break
            if skip:
                continue
            for context in highlight.contexts:
                if (include and context in include) or not include:
                    if not highlight.intensity.level in intensity_filters:
                        print(highlight)
                        highlights_to_return.append(highlight)
                        self.logger.debug(highlight.colorless_str)
                        _count+=1
                        if top and _count == top:
                            return highlights_to_return
                        break
        
        return highlights_to_return


    def print_urls(self, top=None, intensity_filters=[])  -> list[Highlight]:
        """ Prints urls of highlights (with timestamps)

            args:
                top (int, optional): Top n highlights to print, sorted by intensity. Defaults to None, which returns all.
                intensity_filters (list[str]): Intensity levels to filter out. Defaults to [].

            example:
            >>> analyserObject.show_urls():
            >>> "00:02:12 -> https://youtu.be/wAPCSnAhhC8?t=132"
        """
        
        self.logger.info("Printing url's")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{intensity_filters=}")
        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        highlights_to_return = []

        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        print('\n'+Back.RED+"Links:"+Style.RESET_ALL)
        for _count, hl in enumerate(highlights):
            if not hl.intensity.level in intensity_filters:
                print(hl.intensity.color+str(timedelta(seconds=int(hl.time)))+Style.RESET_ALL, '->' ,hl.url)
                self.logger.debug(f"{str(timedelta(seconds=int(hl.time)))} -> {hl.url}")
                highlights_to_return.append(hl)
                if top and _count == top:
                    return highlights_to_return

        return highlights_to_return


    def show_graph(self):
        self.logger.info("Showing graph")
        self.fig.show()


    def find_messages(self, search_phrase, exact=False, ignore_case=True) -> list[Message]:
        """ Finds messages containing a specific phrase.

        Args:
            search_phrase (str): The phrase to search.
            exact (bool, optional): If the phrase has to be exactly the same or not. Defaults to False.
            ignore_case (bool, optional): Ignore letter cases. Defaults to True.

        Returns:
            list[Message]: List of messages that contains the given phrase.
        """
        
        messages_to_return = []
        self.logger.info("Finding messages")
        self.logger.debug(f"{search_phrase=}")
        self.logger.debug(f"{exact=}")
        self.logger.debug(f"{ignore_case=}")

        if ignore_case:
            search_phrase = search_phrase.lower()

        tmp_message = None
        for original_message in self.messages:
            tmp_message = original_message.text
            if ignore_case:
                tmp_message = tmp_message.lower()
            if  (exact and search_phrase == tmp_message) or \
                (not exact and search_phrase in tmp_message):
                messages_to_return.append(original_message)
        self.logger.debug([msg.colorless_str for msg in messages_to_return])
        return messages_to_return


    def find_user_messages(self, id=None, username=None) -> list[Message]:
        """ Finds messages by either username or user id.

        Args:
            id (str, optional): Target user id. Defaults to None.
            username (str, optional): Target username. Defaults to None.
                Note that there might be same users with the same name,
                so it's more reliable to use id

        Raises:
            ValueError: Should provide either username or id.

        Returns:
            list[Message]: Messages the user typed.
        """

        self.logger.info("Finding user messages")
        self.logger.debug(f"{id=}")
        self.logger.debug(f"{username=}")

        if not username and not id:
            self.logger.error("Should provide either username or id")
            raise ValueError("Should provide either username or id.")
        if username and id:
            self.logger.warning("Should only provide one argument. Moving on with id.")
            username=None

        messages_to_return = []
        
        for message in self.messages:
            if  (id and message.author.id == id) or \
                (username and message.author.name == username):
                messages_to_return.append(message)
        self.logger.debug([msg.colorless_str for msg in messages_to_return])
        return messages_to_return


    def most_used_word(self, exclude=[], normalize=True) -> Tuple[str, int]:
        """ Returns most frequently used word

        Args:
            exclude (list, optional): List of words to exclude from the search. Defaults to [].
            normalize (bool, optional): Option for the word be normalized to cover more instances. Defaults to True.

        Returns:
            Tuple[str, int]: Most used word and it's frequency 
        """

        #return "草"    # would probably work lol

        self.logger.info("Finding most used word")
        self.logger.debug(f"{exclude=}")
        self.logger.debug(f"{normalize=}")
        
        if isinstance(exclude, str):
            exclude = list(exclude)
        
        _words = []
        for message in self.messages:
            _words.extend(message.text.split(' '))

        if normalize:
            _words = [utils.normalize(word) for word in _words]
        
        _idx = 0
        while exclude and Counter(_words).most_common(1+_idx)[_idx][0] in exclude:
            _idx+=1
            if _idx == len(_words)-1:
                return Counter(_words).most_common(1+_idx)[_idx]

        self.logger.debug(f"Most used word: {Counter(_words).most_common(1+_idx)[_idx]}")
        return Counter(_words).most_common(1+_idx)[_idx]

    @property
    def total_message_amount(self):
        self.logger.debug(f"Total message amount: {len(self.messages)}")
        return len(self.messages) 


    def __clear_cache(self, id=None):
        """ Deletes cached files of the specified stream.
            Deletes cache of the current id if id is None. """
        if not id:
            id = self.stream_id
        self.logger.info(f"Clearing cache of {id}")
        utils.delete_file(f"{self.config['path-to']['cache']}\\{id}.json.gz")
        utils.delete_file(f"{self.config['path-to']['metadata']}\\{id}.yaml")
        utils.delete_file(f"{self.config['path-to']['thumbnails']}\\{id}.jpg")

    @property
    def least_recently_used_id(self) -> str:
        """ Returns least recenty used stream id """

        least_recently_used_id = None
        last_access_time = time()

        for root, _ , files in os.walk(self.config['path-to']['cache']):
            for name in files:
                path = os.path.join(root, name)
                #if name == self.config['path-to']['test-file']:
                #    continue
                
                if os.path.getatime(path) < last_access_time:
                    last_access_time = os.path.getatime(path)
                    least_recently_used_id = os.path.splitext(os.path.basename(name))[0]

        self.logger.debug(f'Least recently used id: {least_recently_used_id} ({last_access_time})')
        return least_recently_used_id


    def set_thumbnail_url(self, res_lvl=2) -> str:
        """ Sets default thumbnail url
        Args:
            res_lv (int, optional): Resolution level of the thumbnail. Defaults to 2.
                0 -> Medium res.
                1 -> High res.
                2 -> Standard res.
                3 -> Max res.

        Returns:
            dict: Moving average values of the table.

        """
        self.logger.info("Setting thumbnail url")
        self.logger.debug(f"{res_lvl=}")
        if not 0 <= res_lvl < 4:
            self.logger.debug(f"res_lvl was out of range ({res_lvl}), set it to 2")
            res_lvl = 2

        res_lvls = ['mqdefault', 'hqdefault', 'sddefault', 'maxresdefault']
        self.thumbnail_url = f'https://i.ytimg.com/vi/{self.stream_id}/{res_lvls[res_lvl]}.jpg'
        return self.thumbnail_url


    def download_thumbnail(self):
        """ Downloads the thumbnail of the stream to '[path-to-thumbnails]/[id].jpg' """
        self.logger.info("Downloading thumbnail")
        try:
            response = requests.get(self.thumbnail_url)
            with open(f"{self.config['path-to']['thumbnails']}\\{self.stream_id}.jpg", "wb") as f:
                f.write(response.content)
        except Exception as e:
            self.logger.error(f"Couldn't download thumbnail: {e}")

    @property
    def cached_ids(self) -> list[str]:
        """ Returns list of cached ids """
        return [fname.split(os.extsep)[0] for fname in os.listdir(self.config['path-to']['cache'])]

    #TODO Improve integrity checking and point out to missing files
    # themselves directly, and even fix them if possible
    def check_file_integrity(self) -> list[str]:
        """ Checks file integrity and points out any id that has missing files.

        Returns:
            list[str]: List of id's with missing files
        """
        self.logger.info("Checking missing files.")
        cache_folders = [
            self.config['path-to']['cache'],
            self.config['path-to']['metadata'],
            self.config['path-to']['thumbnails']
        ]
        largest_folder = utils.largest_folder(
            self.config['path-to']['cache'],
            self.config['path-to']['metadata'],
            self.config['path-to']['thumbnails']
        )

        id_difference = set([])
        for cache_folder in cache_folders:
            if largest_folder == cache_folder:
                continue
            
            self.logger.debug(f'Checking difference between {largest_folder} and {cache_folder}')
            diffs = list(set(utils.filenames(largest_folder)) - set(utils.filenames(cache_folder)))
            for diff in diffs:
                id_difference.add(diff)
            self.logger.debug(f"Difference is: {diffs}")
        if id_difference:
            __msg = f"Missing files detected for following id's: {id_difference}, consider clearing cache"
            self.logger.warning(__msg)
        else:
            self.logger.debug("No missing files detected.")
        return list(id_difference)

    def enforce_file_integrity(self):
        """ Checks and automatically clears cache of corrupted id's. Use with caution. """
        
        self.logger.info("Enforcing file integrity")
        for corrupted_id in self.check_file_integrity():
            self.__clear_cache(corrupted_id)
