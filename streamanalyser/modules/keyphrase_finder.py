import nltk
import re
import string
import os

PHRASE_END_DELIMITER = "%phrase_end%" # to not mix continous chat messages

NLTK_DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "data", "nltk_data"
)
MONOGRAM_STOP_PUNCTUATIONS_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "data", "monogram_stop_punctuations.txt"
)
MONOGRAM_STOP_WORDS_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "data", "monogram_stop_words.txt"
)


class KeyphraseFinder:
    """A class that finds keyphrases from a live chat using natural language processing
    """
    # TODO more docs

    def __init__(
            self,
            chat,
            monogram_stop_words_path = MONOGRAM_STOP_WORDS_PATH,
            monogram_stop_punctuations_path = MONOGRAM_STOP_PUNCTUATIONS_PATH,
            stop_words_path = None,  # your custom stop words to exclude in collocations
            fix_phrases = [],
            punctuation_list=list(string.punctuation),
        ):

        nltk.download('punkt', download_dir=NLTK_DATA_PATH, quiet=True) 
        nltk.data.path = [NLTK_DATA_PATH]
        
        self.chat = chat
        self.fix_phrases = fix_phrases
        self.punctuation_list = punctuation_list
        self.stop_words_path = stop_words_path

        self.stop_words = None

        # TODO logger

        try:
            # always left an empty whitespace at the end of the txt file
            # get text data line by line
            with open(monogram_stop_words_path, 'r', encoding="utf-8") as file:
                self.monogram_stop_punctuations = [r[:-1] for r in file.readlines()]
            with open(monogram_stop_punctuations_path, 'r', encoding="utf-8") as file:
                self.monogram_stop_words = [r[:-1] for r in file.readlines()]
            if stop_words_path:
                with open(stop_words_path, 'r', encoding="utf-8") as file:
                    self.stop_words = [r[:-1] for r in file.readlines()]
        except FileNotFoundError as e:
            # log
            raise e

        self.monogram_stop_words_all = self.monogram_stop_words + self.monogram_stop_punctuations

    @staticmethod
    def _regex_partition(string, regex):
        if not re.search(regex, string):
            string = string.lower()

        first = re.split(regex, string, 1)[0]
        try:
            last = re.split(regex, string, 1)[1]
        except IndexError:
            last = ''

        regp = re.compile(regex)
        result = regp.search(string)

        try:
            match = result.group()
        except AttributeError:
            match = ''

        return first, match, last

    @staticmethod
    def _tokenize_yt_chat_message(string):
        first, sub_string, last = KeyphraseFinder._regex_partition(string, ":.+:")

        if sub_string:
            tokens = KeyphraseFinder._tokenize_yt_chat_message(last)
            return nltk.word_tokenize(first) + [sub_string] + tokens
        else:
            return nltk.word_tokenize(first)

    def _fix_token(self, token):
        for fix_phrase in self.fix_phrases:
            token = token.replace(fix_phrase[0], fix_phrase[1])
        return token

    def _merge_punctuations(self):
        offset = -1
        for i, token in enumerate(self.tokens):
            if i == len(self.tokens)-1 and offset != -1:
                self.tokens[offset:i+1] = [''.join(self.tokens[offset:i+1])]
                break
            if offset != -1 and token not in self.punctuation_list:
                self.tokens[offset:i] = [''.join(self.tokens[offset:i])]
                offset = -1
            if offset == -1 and token in self.punctuation_list:
                offset = i

    def _adjust_tokens(self):
        if len(self.tokens) == 1 and all([1 if ch in self.punctuation_list else 0 for ch in self.tokens[0]]):
            return
        for i, token in enumerate(self.tokens):
            if len(token) == 1 and all([1 if ch in self.punctuation_list else 0 for ch in token]):
                del self.tokens[i]

    def _tokenize_yt_chat(self):
        self.tokens=[]
        for yt_tokens in [KeyphraseFinder._tokenize_yt_chat_message(msg.text) for msg in self.chat]:
            self._merge_punctuations()
            self._adjust_tokens()
            self.tokens.extend(
                [token for token in list(yt_tokens)]+
                [PHRASE_END_DELIMITER]
            )
        return self.tokens

    @staticmethod
    def _configure_keyphrase_amount(max_keyphrase_amount, min_keyphrase_amount, chat_len, stoppers):
        stoppers = sorted(stoppers, reverse=True)
        for stopper in stoppers:
            if  chat_len < stopper:
                max_keyphrase_amount -= 1
        if max_keyphrase_amount<min_keyphrase_amount:
            max_keyphrase_amount = min_keyphrase_amount
        return max_keyphrase_amount, min_keyphrase_amount

    def ngram_keyphrase_analysis(self, max_ngram_size=7, max_keyphrase_amount=5, min_keyphrase_amount=2, replace_by_weight_score=False, keyphrase_per_ngram=20, min_ngram_size=1, stoppers=[100, 40, 10]) -> list:
        """Returns the most frequently used keyphrases using ngram frequency

            Searches through all ngrams from `max_ngram_size` to `min_ngram_size` to find
            collocations.

            Keyphrases found in ngrams with smaller sizes are overridden by their
            larger ngram counterparts since it's more likely that they contain less
            context.
                Example:
                    Assuming "happy new year" (ngram size is 3) keyphrase is already
                    found, keyphrases such as "new", "happy", "happy new" or "new year"
                    will be excluded from the results since a super-collocation that includes
                    all of them already exists.

            Result frequencies are sorted by their weighted score which is calculated
            with `frequency * ngram_size` formula as of now.

            Returned amount of keyphrases can differ between min and max sizes depending
            on the message amount (lower message amount means less keyphrases).
    
        Args:
            max_ngram_size (int, optional): Max ngram size to search for collocations.
                Lower this value to improve performance. Defaults to 7.
            max_keyphrase_amount (int, optional): Max keyphrase amount to return.
                Defaults to 5.
            min_keyphrase_amount (int, optional): Min keyphrase amount to return. Defaults to 2.
            replace_by_weight_score (bool, optional): [Experimental feature].
                If set to true, ngrams with smaller sizes will replace with their
                super-collocation if they outscore their super-collocation. Defaults to False.
                Example:
                    Considering following keyphrases:
                        "Hello there" (fre: 3, wscore: 6)
                        "Hello" (fre: 21, wscore: 21)
                    Since 21 > 6, "Hello there" will be replaced with "Hello", ignoring
                    "super-ngram contains more context" philosophy.
            keyphrase_per_ngram (int, optional): Top n keyphrases to return per ngram. Defaults to 20.
            min_ngram_size (int, optional): Minimum ngram size to search for collocations.
                Recommened value is 1. Defaults to 1.
            stoppers (int, optional): Fixed message amount points to lower returned keyphrase amount.
                Defaults to [100, 40, 10].

        Returns:
            list: List of most frequent keyphrases
        """

        # TODO parameter validation
        self._tokenize_yt_chat()

        max_keyphrase_amount, min_keyphrase_amount = KeyphraseFinder._configure_keyphrase_amount(
            max_keyphrase_amount, min_keyphrase_amount, len(self.chat), stoppers
        )

        seen_tuples = []
        for ngram_size in range(max_ngram_size, min_ngram_size-1, -1):
            fre_dist_list = nltk.FreqDist(nltk.ngrams(self.tokens, ngram_size)).most_common(keyphrase_per_ngram)
            for fre_tup in fre_dist_list:
                message = self._fix_token(' '.join(fre_tup[0]))
                frequency = fre_tup[1]
                weighted_score = frequency*ngram_size
                if not message:
                    continue
                if frequency <= 1:
                    continue
                if PHRASE_END_DELIMITER in message:
                    continue
                if ngram_size == 1 and message in self.monogram_stop_words:
                    continue
                if ngram_size > 1 and self.stop_words:
                    if any(1 if stop_word in message else 0 for stop_word in self.stop_words):
                        continue
                # punctuation tokens should be considered seperately
                if all(1 if ch in self.punctuation_list else 0 for ch in message):
                    if any([1 for tup in seen_tuples if message == tup[0]]): # already seen
                        continue
                else:
                    skip = False
                    for tup in seen_tuples: 
                        if message in tup[0]: # already seen in higher ngrams
                            if not replace_by_weight_score:
                                skip = True
                                break
                            if weighted_score > tup[3]:
                                seen_tuples.remove(tup)
                            else:
                                skip = True
                            break
                    if skip:
                        continue
                seen_tuples.append((message, frequency, ngram_size, weighted_score)) # TODO keyphrase object

                if len(seen_tuples) == max_keyphrase_amount or ngram_size == min_ngram_size:
                    return sorted(seen_tuples, key=lambda x: x[3], reverse=True)
        return sorted(seen_tuples, key=lambda x: x[3], reverse=True)
