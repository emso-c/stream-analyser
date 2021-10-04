# **Stream Analyser**

### Stream Analyser is a configurable data analysis tool that analyses live streams, detects and classifies highlights based on their intensity, finds keywords, and even guesses contexts.

About context guessing, for now the target environment is *Vtuber streams on YouTube (particularly Hololive)* by default. Though it can be manually configured to satisfy your needs, which will be explained later.

Also can be expanded to other live stream platforms such as Twitch if there's enough support.

> :warning: Seems like wordcloud package can not be installed via pip on win10 right now. You need to manually install the [wheel file](https://pypi.org/project/wordcloud/#files). So I didn't include it in the requirements for now and it is not necessary if you're not gonna use the word cloud feature.

**Currently in Alpha.**

## Table of contents
- [Installation](#Installation)
- [Basic usage](#Usage)
  - [CLI](#with-CLI)
- [Key Features](#Key-features)
- [How does it detect highlights](#About-detecting-highlights)
- [How does it guess contexts](#About-guessing-contexts)
- [Performance](#About-performance)
- [Advanced usage](#Advanced-usage)
    - [1. Fundamentals](#1.-Fundamentals)
      - [Initializing](##initializing-the-object)
      - [analyse() function](#analyse-function)
    - [2. File handling](#2.-File-handling)
      - [Caching](#Caching-1)
      - [Logging](#Logging)
      - [Exporting](#Exporting)
      - [CRUD](#CRUD)
      - [Compressing](#Compressing)
      - [Integrity checking](#Integrity-checking)
    - [3. Logging](#3.-Logging-1)
    - [4. Collecting data](#4.-Collecting-data)
    - [5. Refining data](#5.-Refining-data)
    - [6. Analysing data](#6.-Analysing-data)
    - [7. Output](#7.-Output)
      - [Direct](#Direct)
      - [With prebuilt functions](#With-prebuilt-functions)
    - [8. Custom context](#Custom-context)
- [Testing](#Testing)
- [Possible issues](#Possible-issues)
- [Future goals](#Future-goals)
- [License](#License)

# Installation

Use [pip](https://pip.pypa.io/en/stable/) to install.
```bash
pip install stream-analyser
```

# Usage

```python
import streamanalyser as sa

if __name__ == '__main__':
    with sa.StreamAnalyser("l8Hgi4jF7Zc") as analyser:
        analyser.analyse()
        analyser.get_highlights(top=10, output_mode="detailed")
        analyser.get_highlights(top=10, output_mode="url")
```

Console output:
```bash
Highlights:
[0:02:33] funny: にゃっはろ～, mikokusamikokusamikokusa, mikohatenamikohatenamikohatena, にゃっはろー (773 messages, ultra high intensity, 12.266 diff, 74s duration)
[0:59:24] stream end/funny: mikokusamikokusamikokusa, おつみこ～, おつみこー, おつみこ〜 (799 messages, ultra high intensity, 10.683 diff, 40s duration)  
[0:57:16] funny: mikokusamikokusamikokusa, mikonakimikomikonakimikomikonakimiko, 草, mikokusa (827 messages, ultra high intensity, 9.734 diff, 92s duration)
[0:14:31] good move or play/funny: mikogoodmikogoodmikogood, boing, ないすぅ！, mikokusa (786 messages, ultra high intensity, 9.317 diff, 91s duration)   
[0:18:18] funny: mikogoodmikogoodmikogood, mikokusamikokusamikokusa, mikokusa, 草 (548 messages, very high intensity, 8.396 diff, 44s duration)
[0:11:09] funny: mikokusamikokusamikokusa, 草, mikonakimikomikonakimikomikonakimiko, mikokusa (637 messages, very high intensity, 7.536 diff, 69s duration)
[0:44:21] funny: mikokusamikokusamikokusa, 草, mikokusa, boing (440 messages, very high intensity, 7.512 diff, 47s duration)
[0:08:34] funny: mikokusamikokusamikokusa, mikokusa, 草, mikonakimikomikonakimikomikonakimiko (824 messages, very high intensity, 7.300 diff, 98s duration)
[0:55:01] good move or play: mikogoodmikogoodmikogood, ないすぅ！, mikogood, mikopenmikopmikopenmikopmikopenmikop (432 messages, very high intensity, 7.226 diff, 57s duration)
[0:25:22] funny: mikofapmikofapmikofap, mikokusamikokusamikokusa, mikonakimikomikonakimikomikonakimiko, mikofap (562 messages, very high intensity, 7.168 
diff, 44s duration)

Links:
0:02:33 -> https://youtu.be/l8Hgi4jF7Zc?t=153
0:59:24 -> https://youtu.be/l8Hgi4jF7Zc?t=3564
0:57:16 -> https://youtu.be/l8Hgi4jF7Zc?t=3436
0:14:31 -> https://youtu.be/l8Hgi4jF7Zc?t=871
0:18:18 -> https://youtu.be/l8Hgi4jF7Zc?t=1098
0:11:09 -> https://youtu.be/l8Hgi4jF7Zc?t=669
0:44:21 -> https://youtu.be/l8Hgi4jF7Zc?t=2661
0:08:34 -> https://youtu.be/l8Hgi4jF7Zc?t=514
0:55:01 -> https://youtu.be/l8Hgi4jF7Zc?t=3301
0:25:22 -> https://youtu.be/l8Hgi4jF7Zc?t=1522
```

**Important:** Please see [possible issues](#Possible-issues) if you can't see Japanese characters in console.

## with CLI
You can also use a simple pre-built CLI 

```bash
python -m streamanalyser --help
```
or
```python
from streamanalyser import cli

if __name__ == '__main__':
    cli.main()
```

See "./examples" for more ways to use the module.

# Key features

- Fetch metadata of the stream
  - title, channel name, url etc.
- Fetch live chat of the stream
- Detect highlights
- Guess contexts
- Show highlights
  - Summary
  - Detailed
  - URL
  - Open in browser
- Find messages
- Find authors
- Find messages made by an author
- Visualize data
- Export data

# About detecting highlights

Stream analyser uses live chat reactions to detect highlights and it's accuracy is totally dependant on the participants and the accuracy of the data fetched from YouTube.

# About guessing contexts

Contexts are hard-coded into the `context.json` file and it requires extensive analysis of the target environments demographics and behaviors to determine them.

As stated in the description, the current contexts are based on Vtuber environment by default, but they can be modified according to your needs, which is explained in [custom contexts](#Custom-contexts) section.

# About performance

Stream analyser is optimized to be as fast as possible while minimizing required storage space.

## **Caching**

Stream analyser uses a disk caching mechanism to store useful data such as messages and metadata which would significantly hinder the performance if not cached.

## **Compressing**

Stored messages are compressed right after being fetched and they're only unpacked when needed since they would take up quite a lot of space if not compressed.

## **Exporting**

Other data generated on the run such as graph, word cloud and detected highlights can be exported using `export_data` function.

# **Advanced usage**

# 1. Fundamentals

Stream analyser is divided into sub-modules that handles various parts of the job. To briefly explain each one of them:

- `datacollector`: Collects required data.
- `datarefiner`: Refines collected raw data to be analysed.
- `chatanalyser`: Analyses the refined data.
- `filehandler`: Handles almost everything related to files. Including reading, writing, updating and deleting cached files, logs and exports.
- `structures`: Stores important data models.
- `utils`: Includes various functions that does small jobs.

## Initializing the object

The only required parameter is the id of the stream url. The instance can be initalized as a context manager with the `with` keyword if wanted too:
```python
analyser_object = StreamAnalyser("l8Hgi4jF7Zc")
```
or
```python
with StreamAnalyser("l8Hgi4jF7Zc") as sa:
    ...
```

The other options provide ways to configure methods of analysing, caching, logging and outputting. Full docs can be found in the module. Some of the important ones are:
- `storage_path`: Path to store project related files such as logs and caches.
- `cache_limit`: Max file amount to cache.
- `cache_deletion_algorithm`: In which order the cached files will be deleted.
- `msglimit`: Message amount to fetch.
- `verbose`: Make the output verbose.

## `analyse()` function
Basically the only function needed to analyse a stream. It's a helper function that calls various parts of the whole module in order to analyse the stream. The implementation is as follows:
```python
def analyse(self):
    if not self.is_cached:
        self.collect_data()
    self.enforce_integrity()
    self.read_data()
    self.refine_data()
    self.fetch_missing_messages()
    self.analyse_data()
```
##### P.S. not confuse it with `analyse_data`! 

As can be seen in the code, it collects, reads, refines and finally analyses the data. All while ensuring the integrity and stability withing the package. Each step will be explained later on.

Before diving into the core modules (collector, refiner and analyser), the other helper modules will be explained.

# 2. File handling

File handling is done with the `filehandler` module. It handles everything related to files from caching to interacting with them. These external files are stored in a designated path (Default path is `"C:\Stream Analyser"`)

Example storage folder structure is as follows:
```
Stream Analyser
├───Cache
│   ├───1FXhj4qFOf0
│   ├───hbNdooO8n_M
│   ├───jgp1h2yRbBU
├───Exports
│   ├───1627487676
│   ├───custom_name
└───Logs
```

- ## Caching

    Everytime a stream is analysed, filehandler caches it's files for a much faster access. The cached files are also compressed with gzip to take up less space and only decompressed when used.

    - ### Location and file structure
        filehandler caches the fetched data in `"Stream Analyser/Cache/"`. Inside the cache folder, all streams are cached seperately using the stream id as the folder name and each folder includes a `"messages.json.gz"` and a `"metadata.yaml"` file.

    - ### Cache deletion
        Caches are deleted automatically after hitting the cache limit using a *cache deletion algorithm*. Default behavior is to delete the least recently used cache.
        

- ## Logging

    filehandler deletes logs that are older than the destined log duration (default is 15).

- ## Exporting

    Default export location is stored in filehandler. 

- ## CRUD
    filehandler performs basic CRUD operations to access and manipulate the stored data.

- ## Compressing

    filehandler can compress and decompress files.

- ## Integrity checking
    
    filehandler can check file integrity to detect missing and/or unnecessary files.
    
    It also can automatically fix minor mistakes such as compressing files that are unintentionally left decompressed and deleting unnecessary files.

# 3. Logging

Logging is done with `logging` module. All modules share the same log file that changes weekly and all uses `create_logger` function in `loggersetup` module (except `filehandler`) to initialize their own loggers with their own module names. The reason for using seperate loggers is to improve debugging efficiency. 

Log files use *YYYY-MM-WX.log* naming convention where WX is the Xth week of the month (including 0). Duration of a log file is 15 days (unless chosen to be kept indefinitely) but can be configured. It can also be disabled.

# 4. Collecting data

Data collection is done with the `datacollector` module, which fetches messages of the stream using the `ChatDownloader` module and metadata using the `urllib` module. It also has methods to fetch missing messages and to get thumbnail image url.

One important part to mention is how `msglimit` (message limit) and `iscomplete` works since knowing if all messages are present or not is a crucial information for the module. `msglimit` basically limits the message amount to fetch and it fetches every message if it's set to `None` and `iscomplete` stores if **all** messages are fetched or not judging by message limit. This will help us deciding if the stream is fully cached or not later on.

The fetched data is in it's raw shape and needs to be refined to be actually used.

# 5. Refining data

Data refining is done with the `datarefiner` module. It's a bridge between collector and analyser modules that shapes data from one form to another. 

The raw data collected with `datacollector` is in the dictionary form and it's shaped into `Message` dataclass to make the data more consistent using `refine_raw_messages` function.

It also gets names of the authors and shapes them into `Author` dataclass too.

# 6. Analysing data

Data analysis is done with the `chatanalyser` module by reading the refined chat data.

First, it creates frequency table of the message list and calculates moving average of the table. Then it convolves that data to smoothen the moving average even further, so that the spikes of the function becomes clearer to see. Finally, it detects spikes and marks the spike duration as highlight.

After finding highlight timestamps, other crucial information is analysed to get more information about each highlight such as:
- fdelta: Frequency delta. Difference between the frequency at the start and the end.
- intensity: How tense the highlight was.
- messages: Messages written during the highlight.
- keywords: Most used words during the highlight.
- context: Guessed context by the keywords.
##### (The explained algorithm will be further improved in the future.)

Finally it draws graph of the analysed data.

# 7. Output

- ## Direct
    Data can be accessed directly using the class attributes

    ```python
    print(type(analyser.messages))  # list[Message,Superchat,Membership]
    print(type(analyser.authors))  # list[Author]
    print(type(analyser.highlights))  # list[Higlight]
    print(type(analyser.fig))  # plt
    ```
- ## With prebuilt functions
    There are plenty of prebuilt functions to filter and manipulate the returned data. Assuming the object is initialized as follows:
    
    ```python
    with StreamAnalyser(stream_id) as analyser:
      analyser.analyse()
    ```

    Data can be accessed and manipulated using these functions:

    - `get_highlights`: Returns highlights that can be filtered and sorted by intensity. Can also pretty print to the console using `ouput_mode` argument. Highlights are color coded by intensity.

      ```python
      analyser.get_highlights()
      # No output on console. This usage is the same as `analyser.highlights` and returns a highlight list.

      analyser.get_highlights(top=10)
      # Returns top 10 highlights sorted by intensity.

      analyser.get_highlights(output_mode="summary")
      # Prints the returned highlights on the console.

      analyser.get_highlights(include=["funny", "cute"], exclude=["scary"])
      # Returns highlights that includes "funny" and "cute" contexts and excludes "scary" context. Exclude overrides include. Context names can be found and modified in `.data/contexts.json` file.

      analyser.get_highlights(intensity_filters=["Very high"])
      # Returns highlights that does not have "Very high" intensity. Default intenisty names can be found in `chatanalyser.init_intenisty()` function and modified using arguments when initializing the object. 
      
      ```

    - `most_used_phrase`: Returns most used phrase and its occurance count throughout the stream

      ```python
      # basic usage
      phrase, occurance = analyser.most_used_phrase()
      print(phrase, occurance)
      # lol 74

      # some phrases can be excluded as well
      phrase, occurance = analyser.most_used_phrase(exclude=["lol"])
      print(phrase, occurance)
      # lmao 64

      # phrases are normalized when finding phrases by default but this behavior can be avoided using `normalize` argument.
      phrase, occurance = analyser.most_used_phrase(normalize=False)
      print(phrase, occurance)
      # lol 68 (notice that occurance count is decreased)
      ```

    - `find_messages`: Searches for messages. Can be filtered in various ways.

      ```python
      # basic usage
      found_messages = analyser.find_messages("lol")
      [print(message) for message in found_messages]
      # [0:13:02] Alice: that's funny lol
      # [0:13:15] Bob: lol
      # [0:22:25] William: LOL

      # the exact phrase can be searched
      found_messages = analyser.find_messages("lol", exact=True)
      [print(message) for message in found_messages]
      # [0:13:15] Bob: lol
      # [0:22:25] William: LOL

      # cases are ignored by default, but this behavior can be avoided using `ignore_case` argument. 
      msgs = analyser.find_messages("lol", ignore_case=False)
      [print(message) for message in msgs]
      # [0:13:02] Alice: that's funny lol
      # [0:13:15] Bob: lol
      ```

    - `find_user_messages`: Returns all messages made by an user. Can use either username or id.
      ```python
      found_messages = analyser.find_user_messages(username="Tom")
      [print(message) for message in found_messages]
      # [0:01:42] Tom: That's a nice module

      found_messages = analyser.find_user_messages(
        id="UCHkbYFoYuUpfg2R9jcCkTZg"
      )
      [print(message) for message in found_messages]
      # [1:23:42] Alice: I love cats
      ```
    - `generate_wordcloud`: Creates a basic word cloud of the stream.
      ```python
      analyser.generate_wordcloud().to_image().show()
      ```
    - `show_graph`: Shows a basic graph that contains message frequency and highlights.
      ```python
      # both uses are the same
      analyser.show_graph()
      analyser.fig.show()
      ```

    - `export_data`: Exports analysed data to a specified path.
      ```python
      # basic usage
      # exports data to the default export path with the folder name being the current UNIX timestamp
      analyser.export_data()

      # a custom path and folder name can be used
      # if the folder name is already used, current UNIX timestamp is added after the folder name
      analyser.export_data(
        path="./MyExports", folder_name="MyFolderName"
      )

      # open the folder in file explorer after exporting 
      analyser.export_data(open_folder=True)
      ```

# Custom contexts

To create a custom context list, you can either use `add_context` and `remove_context` functions or rewrite the `context.json` according to your needs.

<hr>

<br>

# Possible issues

### It keeps throwing error when reading cached messages

It's most likely caused by an interrupted I/O operation and the cache needs to be cleared or fixed by hand. Try these in order:

- Run the program again with `reset` option on (`--reset` for CLI).

```python
# solution 1
with StreamAnalyser('Vl_N4AXspo', reset=True) as analyser:
  analyser.collect_data()

# solution 2
with StreamAnalyser('Vl_N4AXspo') as analyser:
  analyser.clear_cache()
  analyser.collect_data()
```
or
```bash
python -m streamanalyser [stream-id] --reset
```

- Open appropriate metadata file and set `is-complete` option to `False`. Then run the program again with `msglimit=None`.

- Delete appropriate message cache by hand.

##### (Default cache path is `"C:\Stream Analyser\Cache\[stream id]"`, or you can directly use the `open_cache_folder` function.)

Should the error persists, please open an issue.

### Can't see Japanese characters on console

Just changing the code page to `932` should work.

```bash
C:\Your\Path> chcp 932
Active code page: 932

C:\Your\Path> 今日本語が書ける
```

Likewise, use `chcp 65001` to go back. Or simply re-open the console.

## Testing

```python
python -m unittest discover test
```

```python
python test_coverage.py
```

## Future goals

- Expand to other stream platforms.

- Automatize context guessing.

- End world hunger.

## License
[GPL v3.0](https://choosealicense.com/licenses/gpl-3.0/)