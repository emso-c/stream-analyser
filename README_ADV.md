# Fundamentals

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

The other options provide ways to configure methods of analysing, caching, logging and output. Full docs can be found in the module. Some of the important ones are:
- `storage_path`: Path to store the related files such as logs and caches.
- `cache_limit`: Max stream amount to cache.
- `cache_deletion_algorithm`: In which order the cached files will be deleted.
- `msglimit`: Message amount to fetch.
- `verbose`: Make the output verbose.

## `analyse` function
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

# File handling

File handling is done with the `filehandler` module. It handles everything related to files from caching to interacting with them. Those external files are store in a designated path (Default path is `"C:\Stream Analyser"`)

Example folder structure is as follows:
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

# Logging

Logging is done with `logging` module. All modules share the same log file that changes weekly and all uses `create_logger` function in `loggersetup` module (except `filehandler`) to initialize their own loggers with their own module names. The reason for using seperate loggers is to improve debugging efficiency. 

Log files use *YYYY-MM-WX.log* naming convention where WX is the Xth week of the month (including 0). Duration of a log file is 15 days (unless chosen to be kept indefinitely) but can be configured. It can also be disabled.

# Collecting data

Data collection is done with the `datacollector` module, which fetches messages of the stream using the `ChatDownloader` module and metadata using the `urllib` module. It also has methods to fetch missing messages and to get thumbnail image url.

One important part to mention is how `msglimit` (message limit) and `iscomplete` works since knowing if all messages are present or not is a crucial information for the module. `msglimit` basically limits the message amount to fetch and it fetches every message if it's set to `None` and `iscomplete` stores if **all** messages are fetched or not judging by message limit. This will help us deciding if the stream is fully cached or not later on.

The fetched data is in it's raw shape and needs to be refined to be actually used.

# Refining data

Data refining is done with the `datarefiner` module. It's a bridge between collector and analyser modules that shapes data from one form to another. 

The raw data collected with `datacollector` is in the dictionary form and it's shaped into `Message` dataclass to make the data more consistent using `refine_raw_messages` function.

It also gets names of the authors and shapes them into `Author` dataclass too.

# Analysing data

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

# Output

- ## Direct
    Data can be accessed directly using the class attributes

    ```python
    print(type(analyser.messages))  # list[Message]
    print(type(analyser.authors))  # list[Author]
    print(type(analyser.highlights))  # list[Higlight]
    print(type(analyser.fig))  # plt
    ```
- ## With prebuilt functions
    There are plenty of prebuilt functions to access filter and manipulate the returned data.

    - `get_highlights`: Returns highlights that can be filtered and sorted by intensity. Can also pretty print to the console using `ouput_mode`. Highlights are color coded by intensity.

    - `most_used_phrase`: Returns most used phrase throughout the stream

    - `find_messages`: Searches for filtered messages.

    - `find_user_messages`: Returns all messages made by an user.

    - `generate_wordcloud`: Creates a basic word cloud of the stream.

    - `show_graph`: Shows a basic graph that contains message frequency and highlights.

    - `export_data`: Exports analysed data to a specified path.
