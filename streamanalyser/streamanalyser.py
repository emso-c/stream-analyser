from collections import Counter
from datetime import timedelta
import os
import random
import traceback
from shutil import copyfile
from typing import Tuple
from time import time
from colorama.ansi import Back, Style

from wordcloud import WordCloud

from .modules import (
    loggersetup,
    filehandler,
    datacollector,
    datarefiner,
    chatanalyser,
    structures,
    utils,
    cli,
)

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CONTEXT_SOURCE_PATH = os.path.join(DIR_PATH, "data", "default_contexts.json")
DEFAULT_FONT_PATH = os.path.join(DIR_PATH, "fonts", "NotoSansCJKjp-Bold.ttf")
with open(rf"{DIR_PATH}/data/keyword_filters.txt", "r", encoding="utf-8") as f:
    DEFAULT_KEYWORD_FILTERS = [kw.strip("\n") for kw in f.readlines()]
DEFAULT_STORAGE_PATH = structures.DefaultStoragePath.get_path()

class StreamAnalyser:
    """A class that analyses live streams.

    Args:
        sid (str): Video id of the stream.

        msglimit (int|None, optional): Message amount to fetch. Defaults to None.

        verbose (bool, optional): Print output to console. Defaults to False.

        thumb_res_lvl (int, optional): Resolution level of the thumbnail.
            Resolution levels are sorted by quality with 0 being lowest
            and 3 being highest. Defaults to 2.

        yt_api_key (str, optional): YouTube API key to provide full functionality.
            The class would still work 99% even if the api key is not provided, So
            it is not necessary, but still recommended for edge cases.
            Defaults to None.

        disable_logs (bool, optional): Disable logging.
            Log files' location can be found in `filehandler` module.
            Defaults to False.

        keep_logs (bool, optional): Do not delete logs. See `log_duration`
            for more information. Defaults to False.

        log_duration (int, optional): Log duration in days. Logs that are
            older than this value will be deleted if `keep_logs` option is
            False. Cache of the current week can only be deleted after 7 days.
            Defaults to 15.

        storage_path (str, optional): Folder to store files related to this
            module. Defaults to DEFAULT_STORAGE_PATH.

        reset (bool, optional): Clear existing cache when initializing the object.
            Defaults to False

        not_cache(bool, optional): Not cache stream data when using
            `analyse` function. Isn't recommended to use since fetching
            live chat messages takes quite a lot of time. The mere use-case
            is if the data will be used only for once. Even so, the cache
            can be deleted later on with the `clear_cache` function. Defaults
            to False.

        keep_cache (bool, optional): Do not delete any of the cached
            files, anytime (except the current session's cache if
            `not_cache` is True). Isn't recommended to use since lots
            of cached data might take up unnecessary space if not
            handled. If set to False, cached data will be deleted
            occasionally according to the chosen algorithm. See
            `cache_deletion_algorithm` for more info. Defaults to False.

        cache_deletion_algorithm (str, optional): Algorithm to delete
            cached files. Options are as follows:
                - lru (Least recently used): Deletes least recently
                    used cache. (recommended)
                - mru (Most recently used): Deletes most recently
                    used cache.
                - fifo (First in first out): Deletes oldest cache.
                - rr (Random replacement): Deletes random cache. (uhh...)
            Defaults to 'lru'.

        cache_limit (int, optional): Cache file amount to keep. Cached
            files will be deleted if file amount exceeds this value
            according to `cache_deletion_algorithm` option. Defaults to 50.

        min_duration (int): Minimum highlight duration (in seconds) to detect.
            Defaults to 5

        window (int, optional): Time interval to calculate moving averages.
            Defaults to 30.

        threshold_constant(int, optional): The value that divides average
            highlight duration. Defaults to 3.

        keyword_limit(int, optional): Keyword amount to retrieve. Defaults to 4.

        keyword_filters(list, optional): Keywords to filter. Defaults to [].

        intensity_levels (list[str], optional): See `init_intensity` function in
            `chat_analyser` module for information. Defaults to [].

        intensity_constants (list[str], optional): See `init_intensity` function in
            `chat_analyser` module for information. Defaults to [].

        intensity_colors (list[str], optional): See `init_intensity` function in
            `chat_analyser` module for information. Defaults to [].

        keep_analysis_data (bool, optional): Keeps analysis data such as message
            frequency, moving average and annotations until the object terminates.
            Set to False to conserve more memory during runtime if the data won't be
            needed. Defaults to True.

        default_context_path (str, optional): Default path to context json file.
            Defaults to DEFAULT_CONTEXT_SOURCE_PATH.

        stop_words_path (bool, optional): Default stop word file (.txt) path to exclude in
            keyphrase collocations. Defaults to None.
    """

    def __init__(
        self,
        sid,
        msglimit=None,
        verbose=False,
        thumb_res_lvl=2,
        yt_api_key=None,
        disable_logs=False,
        keep_logs=False,
        log_duration=15,
        storage_path=DEFAULT_STORAGE_PATH,
        reset=False,
        not_cache=False,
        keep_cache=False,
        cache_deletion_algorithm="lru",
        cache_limit=50,
        min_duration=15,
        window=30,
        threshold_constant=3,
        keyword_limit=4,
        keyword_filters=[],
        intensity_levels=[],
        intensity_constants=[],
        intensity_colors=[],
        keep_analysis_data=True,
        default_context_path=DEFAULT_CONTEXT_SOURCE_PATH,
        stop_words_path = None
    ):

        self.sid = sid
        self.msglimit = msglimit
        self.verbose = verbose
        self.thumb_res_lvl = thumb_res_lvl
        self.yt_api_key = yt_api_key
        self.disable_logs = disable_logs
        self.not_cache = not_cache
        self.keep_cache = keep_cache
        self.cache_limit = cache_limit
        self.min_duration = min_duration
        self.window = window
        self.threshold_constant = threshold_constant
        self.keyword_limit = keyword_limit
        self.keyword_filters = keyword_filters + DEFAULT_KEYWORD_FILTERS
        self.intensity_levels = intensity_levels
        self.intensity_constants = intensity_constants
        self.intensity_colors = intensity_colors
        self.keep_analysis_data = keep_analysis_data
        self.default_context_path = default_context_path
        self.stop_words_path = stop_words_path

        self._raw_messages = {}
        self.messages = []
        self.authors = []
        self.highlights = []
        self.wordcloud = None
        self.fig = None
        self.metadata = {}
        self.context_source = structures.ContextSourceManager([])

        self.filehandler = filehandler.FileHandler(storage_path=storage_path)
        self.logger = loggersetup.create_logger(__file__, self.filehandler.log_path, sid=sid)
        self.collector = datacollector.DataCollector(sid, log_path=self.filehandler.log_path, msglimit=msglimit, verbose=verbose, yt_api_key=yt_api_key)
        self.refiner = datarefiner.DataRefiner(log_path=self.filehandler.log_path, verbose=verbose)
        self.canalyser = None  # It's recommended to empty this variable by hand to conserve memory after using the analysis data. See `keep_analysis_data` option for more.

        if disable_logs:
            self._disable_logs()

        if not keep_logs:
            self.filehandler._delete_old_files(self.filehandler.log_path, log_duration)
        self.logger.info(("=" * 100) + "=" * 15)
        self.logger.info(f"{'='*20} SESSION START {'='*80}")
        self.logger.info(("=" * 100) + "=" * 15)
        
        self.logger.info("Analyser initiated with following parameters:")
        self.logger.debug(f"{msglimit=}")
        self.logger.debug(f"{verbose=}")
        self.logger.debug(f"{thumb_res_lvl=}")
        self.logger.debug(f"{yt_api_key=}")
        self.logger.debug(f"{disable_logs=}")
        self.logger.debug(f"{keep_logs=}")
        self.logger.debug(f"{log_duration=}")
        self.logger.debug(f"{storage_path=}")
        self.logger.debug(f"{reset=}")
        self.logger.debug(f"{not_cache=}")
        self.logger.debug(f"{keep_cache=}")
        self.logger.debug(f"{cache_deletion_algorithm=}")
        self.logger.debug(f"{cache_limit=}")
        self.logger.debug(f"{min_duration=}")
        self.logger.debug(f"{window=}")
        self.logger.debug(f"{threshold_constant=}")
        self.logger.debug(f"{keyword_limit=}")
        self.logger.debug(f"{keyword_filters=}")
        self.logger.debug(f"{intensity_levels=}")
        self.logger.debug(f"{intensity_constants=}")
        self.logger.debug(f"{intensity_colors=}")
        self.logger.debug(f"{keep_analysis_data=}")
        self.logger.debug(f"{default_context_path=}")
        self.logger.debug(f"{stop_words_path=}")


        self.filehandler.create_cache_dir(self.sid)
        if reset:
            self.clear_cache(delete_root_folder=False)

        if not keep_cache:
            famount = self.filehandler.dir_amount(self.filehandler.cache_path)
            if cache_limit < 1:
                raise ValueError("Cache limit must be a natural number")
            if famount > cache_limit:
                self.logger.warning(
                    f"Cache limit has been exceeded by {famount-cache_limit}"
                )
            while famount > cache_limit:
                self.clear_cache(cache_deletion_algorithm)
                famount -= 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
        if self.not_cache:
            self.clear_cache()

    def _disable_logs(self):
        self.logger.disabled = True
        self.filehandler.logger.disabled = True
        self.collector.logger.disabled = True
        self.refiner.logger.disabled = True

    def _cache_metadata(self, metadata):
        self.filehandler.cache_metadata(metadata)

    def _cache_messages(self, raw_messages):
        self.filehandler.cache_messages(raw_messages)

    def clear_cache(self, cache_deletion_algorithm=None, delete_root_folder=True):
        self.filehandler.clear_cache(cache_deletion_algorithm, delete_root_folder)

    def collect_data(self):
        """Collects and caches stream data:
        - messages
        - metadata (title, channel, duration etc.)
        """
        # collect data
        metadata = self.collector.collect_metadata()
        raw_messages = self.collector.fetch_raw_messages()

        # cache data
        self._cache_metadata(metadata)
        self._cache_messages(raw_messages)

    def read_data(self):
        """Reads cached data"""
        if self.verbose:
            print("Reading messages...", end="\r")

        self._raw_messages = self.filehandler.read_messages()
        self.update_metadata(self.filehandler.read_metadata())

        if "is-complete" in self.metadata.keys():
            if not self.metadata["is-complete"]:
                self.update_metadata({"is-complete": self.collector.iscomplete})
        else:
            self.update_metadata({"is-complete": self.collector.iscomplete})

        if self.verbose:
            print("Reading messages... done")

    def refine_data(self):
        """Refines read data"""
        self.messages = self.refiner.refine_raw_messages(
            self._raw_messages, self.msglimit
        )
        # we don't need raw messages anymore
        # empty them so they don't take up space
        self._raw_messages = None
        self.authors = self.refiner.get_authors()

    def analyse_data(self):
        """Analyses refined data and detects highligths"""
        self.canalyser = chatanalyser.ChatAnalyser(
            log_path=self.filehandler.log_path,
            refined_messages=self.messages,
            default_context_path=self.default_context_path,
            stream_id=self.sid,
            verbose=self.verbose,
            keyword_filters=self.keyword_filters,
            keyword_limit=self.keyword_limit,
            min_duration=self.min_duration,
            threshold_constant=self.threshold_constant,
            window=self.window,
            stop_words_path=self.stop_words_path
        )
        if self.disable_logs:
            self.canalyser.logger.disabled = True
        self.canalyser.source.paths.extend(self.context_source.paths)

        self.canalyser.analyse(
            levels=self.intensity_levels,
            constants=self.intensity_constants,
            colors=self.intensity_colors,
            autofix_context_collision=True
        )
        self.highlights = self.canalyser.highlights

        if not self.keep_analysis_data:
            self.canalyser = None

    def analyse(self):
        if not self.is_cached:
            self.collect_data()
        self.read_data()
        self.refine_data()
        self.enforce_integrity()
        self.fetch_missing_messages()
        self.analyse_data()

    def _check_integrity(self, autofix=False) -> Tuple[list, list]:
        return self.filehandler.check_integrity(autofix=autofix)

    @property
    def is_cached(self):
        return self.filehandler.is_cached()

    def fetch_missing_messages(self):
        """Checks and fetches missing messages if there's any.
        Should be used when the message limit is increased or
        set to None. It also caches, reads and refines the
        messages by itself as well.

        For instance if 1000 messages had been fetched before,
        and the user is requesting 1200 messages now, the function
        will only fetch the last 200 messages instead of starting
        all over again.
        """

        self.logger.info("Checking missing messages")

        if "is-complete" not in self.metadata.keys():
            self.logger.debug(
                "Could not fetch missing messages since messages are not collected yet"
            )
            return

        if self.metadata["is-complete"]:
            self.logger.debug("Messages are already complete")
            return
        if self.verbose:
            print("Checking missing messages...", end="\r")

        raw_messages = self.filehandler.read_messages()
        last_time = raw_messages[-1]["time_in_seconds"]
        current_amount = len(raw_messages)

        if not self.metadata["is-complete"] and not self.msglimit:
            target_amount = None
        else:
            target_amount = self.msglimit - current_amount
            if target_amount <= 0:
                self.logger.debug("No missing messages detected")
                if self.verbose:
                    print("Checking missing messages... done")
                return

        if self.verbose:
            print("Checking missing messages... done")

        missing_messages = self.collector.fetch_missing_messages(
            start_time=last_time,
            current_amount=current_amount,
            target_amount=target_amount,
        )
        self.filehandler.cache_messages(raw_messages + missing_messages)
        self.messages = self.messages + self.refiner.refine_raw_messages(
            missing_messages
        )
        self.authors = self.authors + self.refiner.get_authors()
        self.update_metadata({"is-complete": self.collector.iscomplete})

    def update_metadata(self, new_dict):
        """Updates both metadata file and variable"""
        self.metadata = {**self.metadata, **new_dict}
        self.filehandler.cache_metadata(self.metadata)
        self.logger.info("Updated metadata")

    def enforce_integrity(self):
        """Enforces file integrity by recollecting missing
        data and deleting unnecessary cache files"""

        missing_files, _ = self._check_integrity(autofix=True)
        for missing_file in missing_files:
            if missing_file == self.filehandler.message_fname + ".gz":
                self.logger.warning("Message file is missing")
                self.filehandler.cache_messages(self.collector.fetch_raw_messages())
            elif missing_file == self.filehandler.metadata_fname:
                self.logger.warning("Metadata file is missing")
                self.filehandler.cache_metadata(self.collector.collect_metadata())

        try:
            # TODO fix logic
            #self.fetch_missing_messages()
            pass
        except KeyError:
            pass
        except Exception as e:
            self.logger.error(e.__class__.__name__ + e)

    def generate_wordcloud(self, font_path=None, scale=3, background="aliceblue"):
        """Returns a basic word cloud

        Args:
            font_path (str, optional): Custom font path. Defaults to None.
            scale (int, optional): Scale of the resulting wordcloud.
                Might want to decrease it for more performance. Defaults to 3.
            background (str, optional): Background color. Defaults to "aliceblue".
        """

        self.logger.info("Generating word cloud")
        self.logger.debug(f"{font_path=}")
        self.logger.debug(f"{scale=}")
        self.logger.debug(f"{background=}")

        if self.verbose:
            print("Generating word cloud...", end="\r")

        if not font_path:
            font_path = DEFAULT_FONT_PATH

        # get all words from the chat
        wordlist = [msg.text.replace("_", "") for msg in self.messages]

        # shuffle word list to minimize the issue where repeating
        # consecutive messages merge together in the word cloud
        random.shuffle(wordlist)

        try:
            word_cloud = WordCloud(
                font_path=font_path,
                scale=scale,
                background_color=background,
            ).generate(" ".join(wordlist))
        except Exception as e:
            self.logger.error(f"Could not generate wordcloud: {e}")
            if self.verbose:
                print("Generating word cloud... error")
            raise e

        if self.verbose:
            print("Generating word cloud... done")
        self.wordcloud = word_cloud
        return self.wordcloud

    def find_messages(
        self, search_phrase, exact=False, ignore_case=True
    ) -> list[structures.Message, structures.Superchat, structures.Membership]:
        """Finds messages containing a specific phrase or exactly the same phrase.

        Args:
            search_phrase (str): The phrase to search.
            exact (bool, optional): If the phrase has to be exactly the same or not. Defaults to False.
            ignore_case (bool, optional): Ignore letter cases. Defaults to True.

        Returns:
            list[Message,Superchat,Membership]: List of messages that contains the given phrase.
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
            if (exact and search_phrase == tmp_message) or (
                not exact and search_phrase in tmp_message
            ):
                messages_to_return.append(original_message)
        return messages_to_return

    def find_user_messages(self, username=None, id=None) -> list[structures.Message, structures.Superchat, structures.Membership]:
        """Finds messages by either username or user id.

        Args:
            username (str, optional): Target username. Defaults to None.
                Note that it's more reliable to use id since there might
                be same users with the same name or username changes.

            id (str, optional): Target user id. Defaults to None.

        Raises:
            ValueError: Should provide either username or id.

        Returns:
            list[Message,Membership,Superchat]: Messages the user typed.
        """

        self.logger.info("Finding user messages")
        self.logger.debug(f"{id=}")
        self.logger.debug(f"{username=}")

        if not username and not id:
            self.logger.error("Should provide either username or id")
            raise ValueError("Should provide either username or id.")
        if username and id:
            self.logger.warning("Should only provide one argument. Moving on with id.")
            username = None

        messages_to_return = []
        for message in self.messages:
            if (id and message.author.id == id) or (
                username and message.author.name == username
            ):
                messages_to_return.append(message)

        return messages_to_return

    def most_used_phrase(self, exclude=[], normalize=True) -> Tuple[str, int]:
        """Returns most frequently used phrase

        Args:
            exclude (list, optional): List of words to exclude from the search.
                Defaults to [].

            normalize (bool, optional): Option for the word be normalized
                to cover more instances. Defaults to True.

        Returns:
            Tuple[str, int]: Most used word and it's frequency
        """

        # return "草"    # would probably work lol

        self.logger.info("Finding most used word")
        self.logger.debug(f"{exclude=}")
        self.logger.debug(f"{normalize=}")

        if isinstance(exclude, str):
            exclude = list(exclude)

        words = []
        for message in self.messages:
            words.extend(message.text.split(" "))

        if normalize:
            words = [utils.normalize(word) for word in words]

        idx = 0
        while exclude and Counter(words).most_common(1 + idx)[idx][0] in exclude:
            idx += 1
            if idx == len(words) - 1:
                return Counter(words).most_common(1 + idx)[idx]

        self.logger.debug(f"Most used phrase: {Counter(words).most_common(1+idx)[idx]}")
        return Counter(words).most_common(1 + idx)[idx]

    @property
    def total_message_amount(self):
        return len(self.messages)

    def export_data(self, folder_name=None, path=None, open_folder=False):
        """Exports the analysed data to the path.
        Exported data are:
        - messages
        - highlights
        - metadata
        - thumbnail
        - graph
        - word cloud

        Args:
            folder_name (str|None, optional): File name to export the results. Defaults to None,
                which exports data under the file named current UNIX timestamp.
            path (str|None, optional): Path to export the results. Defaults to None,
                which exports data to the default path.
            open_folder (bool, optional): Open the export folder in file explorer
                after exporting. Defaults to false

        """

        self.logger.info("Exporting data")
        self.logger.debug(f"{folder_name=}")
        self.logger.debug(f"{path=}")

        if self.verbose:
            print("Exporting data...", end="\r")

        if not path:
            path = self.filehandler.export_path

        try:
            self.filehandler.create_dir_if_not_exists(path)
        except PermissionError as pe:
            self.logger.error(pe)
            return

        if not folder_name:
            folder_name = str(int(time()))
        else:
            # check if there's already a file with the same name
            # if so, add UNIX timestamp to make it unique
            for name in os.listdir(path):
                if os.path.isdir(os.path.join(path, name)) and name == folder_name:
                    folder_name = folder_name + "_" + str(int(time()))
                    warn_msg = f"{name} already exists, renaming to {folder_name}"
                    self.logger.warning(warn_msg)
                    break

        target_path = path + "\\" + folder_name
        self.filehandler.create_dir_if_not_exists(target_path)

        # export messages
        self.filehandler._decompress_file(
            os.path.join(self.filehandler.sid_path, self.filehandler.message_fname)
        )
        copyfile(
            src=os.path.join(self.filehandler.sid_path, self.filehandler.message_fname),
            dst=os.path.join(target_path, self.filehandler.message_fname),
        )
        self.filehandler._compress_file(
            os.path.join(self.filehandler.sid_path, self.filehandler.message_fname)
        )
        self.logger.info("Exported messages")

        # export metadata
        copyfile(
            src=os.path.join(
                self.filehandler.sid_path, self.filehandler.metadata_fname
            ),
            dst=os.path.join(target_path, self.filehandler.metadata_fname),
        )
        self.logger.info("Exported metadata")

        # export thumbnail
        self.filehandler.download_thumbnail(
            self.collector.get_thumbnail_url(self.thumb_res_lvl),
            os.path.join(target_path, self.filehandler.thumbnail_fname),
        )
        self.logger.info("Exported thumbnail")

        # export word cloud
        if self.messages:
            self.generate_wordcloud().to_file(
                os.path.join(target_path, "wordcloud.jpg")
            )
            self.logger.info("Exported wordcloud")

        # export highlights
        if self.highlights:
            hl_path = os.path.join(target_path, "highlights.txt")
            with open(hl_path, "w", encoding="utf-8") as file:
                file.writelines([hl.colorless_str + "\n" for hl in self.highlights])
            self.logger.info("Exported highlights")

        if self.fig:
            self.fig.savefig(os.path.join(target_path, "graph.png"))
            self.logger.info("Exported graph")

        if open_folder:
            try:
                os.startfile(target_path)
                self.logger.info(f"Opened {target_path} in file explorer")
            except FileNotFoundError:
                self.logger.error(f"Couldn't find {target_path}")

        if self.verbose:
            print("Exporting data... done")

    def get_highlights(
        self, top=None, output_mode=None, include=[], exclude=[], intensity_filters=[]
    ) -> list[structures.Highlight]:
        """A method to return filtered highlights.

        Args:
            top (int, optional): Top n highlights to fetch, sorted by fdelta attribute.
                Defaults to None, which returns all.

            output_mode (str, optional): Mode to print output of the highlights on
                the console. Options are:
                    - 'detailed': Show details of the highlights.
                    - 'summary': Show only time and intensity of the highlights
                    - 'url': Show only time and url of the highlights
                    - None: No output.
                Defaults to None.

            include (list[str]|str, optional): List of reactions to see. Defaults to [].
                Reaction names can be found in `data\context.json`.

            exclude (list[str]|str, optional): List of reactions to not see.
                Overrides include. Defaults to [].
                Reaction names can be found in `data\context.json`.

            intensity_filters (list[str]|str, optional): Intensity levels to filter out.
                Defaults to [].

        Returns:
            list[Highlight]: List of highlights
        """

        self.logger.info("Printing highlights")
        self.logger.debug(f"{top=}")
        self.logger.debug(f"{output_mode=}")
        self.logger.debug(f"{include=}")
        self.logger.debug(f"{exclude=}")
        self.logger.debug(f"{intensity_filters=}")

        if isinstance(include, str):
            include = list(include)
        if isinstance(exclude, str):
            exclude = list(exclude)
        if isinstance(intensity_filters, str):
            intensity_filters = list(intensity_filters)

        if top and top < 0:
            self.logger.error("Top value cannot be negative")
            raise ValueError("Top value cannot be negative.")

        count = 0
        highlights_to_return = []
        if top:
            highlights = sorted(self.highlights, key=lambda x: x.fdelta, reverse=True)
        else:
            highlights = self.highlights

        if output_mode:
            if output_mode == "detailed":
                title = "Highlights:"
            elif output_mode == "url":
                title = "Links:"
            elif output_mode == "summary":
                title = "Summary:"
            else:
                self.logger.error("Invalid output_mode")
                raise ValueError("Invalid output_mode")
            print("\n" + Back.RED + title + Style.RESET_ALL)
        for highlight in highlights:
            skip = False
            for context in highlight.contexts:
                if exclude and context in exclude:
                    skip = True
                    break
            if skip:
                continue
            for context in highlight.contexts:
                if (include and context in include) or not include:
                    if not highlight.intensity.level in intensity_filters:
                        if output_mode == "detailed":
                            print(highlight)
                        elif output_mode == "summary":
                            print(
                                "{}: {}".format(
                                    timedelta(seconds=int(highlight.time)),
                                    highlight.intensity.colored_level,
                                )
                            )
                        elif output_mode == "url":
                            print(
                                highlight.intensity.color
                                + str(timedelta(seconds=int(highlight.time)))
                                + Style.RESET_ALL,
                                "->",
                                highlight.url,
                            )
                        elif output_mode is None:
                            pass
                        else:
                            self.logger.error("Invalid output mode")
                            raise ValueError(f'Invalid output mode: "{output_mode}"')
                        highlights_to_return.append(highlight)
                        self.logger.debug(highlight.colorless_str)
                        count += 1
                        if top and count == top:
                            return highlights_to_return
                        break

        return highlights_to_return

    def add_context(self, reaction_to, phrases):
        self.filehandler.add_context(reaction_to, phrases)

    def remove_context(self, reaction_to):
        self.filehandler.remove_context(reaction_to)

    def cached_ids(self) -> list[str]:
        return self.filehandler.get_cached_ids()

    def open_cache_folder(self):
        self.filehandler.open_cache_folder(self.sid)

    def show_graph(self):
        self.canalyser.draw_graph(self.metadata["title"])
        self.fig = self.canalyser.fig
        self.fig.show()


if __name__ == "__main__":
    cli.main()
