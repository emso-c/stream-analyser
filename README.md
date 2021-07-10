# Stream Analyser

### Stream Analyser is a configurable data analysis tool that analyses live streams, detects and classifies highlights based on their intensity, finds keywords, and even guesses contexts.

For now the target environment is *Vtuber streams on YouTube (particularly Hololive)* by default. Though it can be manually configured to satisfy your needs, which will be explained later.

Also can be expanded to other live stream platforms such as Twitch if there's enough support.

**Currently in Alpha.**

## Table of contents
- [Installation](#Installation)
- [Usage](#Usage)
  - [CLI](#with-CLI)
- [Key Features](#Key-features)
- [How does it detect highlights](#About-detecting-highlights)
- [How does it guess contexts](#About-guessing-contexts)
- [Advanced usage](#Advanced-usage)
    - [TODO](#)
- [Possible issues](#Possible-issues)
- [Future goals](#Future-goals)
- [License](#License)

## Installation

Use [pip](https://pip.pypa.io/en/stable/) to install.
```bash
pip install stream-analyser
```

## Usage

```python
from streamanalyser import streamanalyser as sa

if __name__ == '__main__':
    id = 'Vl_N4AXspo'  # id of the stream, not the whole URL.
    analyser = sa.StreamAnalyser(id)
    analyser.analyse()
    analyser.print_highlights(top=10)
    analyser.print_urls(top=10)
```

Console output:
```bash
Highlights:
[1:57:35] stream end/understood: はーい, おつぺこー, おつぺこ～, bye (331 messages, ultra high intensity, 3.479 diff, 48s duration)
[0:00:01] None: にーんじんpekoにんじんにーんじんpekoにんじん, ninjin, にーん…, にーん (406 messages, ultra high intensity, 3.309 diff, 87s duration)
[2:02:12] None: さんっpekoびっくりまーくpekoおーっ, 停车, peko, さんっ！ (246 messages, ultra high intensity, 3.008 diff, 61s duration)
[1:00:17] funny moment: moona, hey, moon, 草 (361 messages, ultra high intensity, 2.823 diff, 78s duration)
[1:30:27] funny moment: peko, わーお, big, lol (365 messages, very high intensity, 2.570 diff, 82s duration)
[1:40:12] funny moment: 草, lol, peko, わーお (226 messages, very high intensity, 2.531 diff, 48s duration)
[1:06:24] shocked or suprised: ！？, え, え？, en (225 messages, very high intensity, 2.312 diff, 61s duration)
[1:13:50] funny moment/shocked or suprised: 草, ！？, lol, わーお (304 messages, very high intensity, 2.258 diff, 64s duration)
[1:16:38] funny moment: peko焦り顔peko焦り顔peko焦り顔, ｺﾆﾁﾜｰ, 草, こわ (235 messages, very high intensity, 2.232 diff, 41s duration)
[1:28:12] funny moment/cute moment/shocked or suprised: 草, はいぃ…, かわいい, あ (303 messages, very high intensity, 2.189 diff, 75s duration)

Links:
1:57:35 -> https://youtu.be/K1RayPkG9xQ?t=7055
0:00:01 -> https://youtu.be/K1RayPkG9xQ?t=1
2:02:12 -> https://youtu.be/K1RayPkG9xQ?t=7332
1:00:17 -> https://youtu.be/K1RayPkG9xQ?t=3617
1:30:27 -> https://youtu.be/K1RayPkG9xQ?t=5427
1:40:12 -> https://youtu.be/K1RayPkG9xQ?t=6012
1:06:24 -> https://youtu.be/K1RayPkG9xQ?t=3984
1:13:50 -> https://youtu.be/K1RayPkG9xQ?t=4430
1:16:38 -> https://youtu.be/K1RayPkG9xQ?t=4598
1:28:12 -> https://youtu.be/K1RayPkG9xQ?t=5292
```

**Important:** Please see [possible issues](#Possible-issues) if you can't see Japanese characters in console.

###### Side note: Notice that the first two highlights will most likely be at the start and the end of the stream when highlights are sorted.

### with CLI
You can also use a simple pre-built CLI 

```python
# cli.py
from streamanalyser import streamanalyserCLI

if __name__ == '__main__':
    streamanalyserCLI.main()
```
```bash
python cli.py --help
```

## Key features

- Fetch metadata of the stream
  - title, author, thumbnail etc.
- Fetch live messages of the stream
- Create frequency table of messages
- Detect highlights
- Get keywords
- Guess contexts
- Show highlights
  - Summary
  - Detailed
  - URL
  - Open in Chrome
- Find messages
- Find authors
- Find messages made by an author
- Visualize the data
- Export the data

## About detecting highlights

Stream analyser uses live chat to detect highlights. First, it creates frequency table of the messages and calculates moving average of the table. Then it convolves that data to smoothen the moving average even further, so that the spikes of the function becomes clearer to see. Finally, it detects spikes and marks the spike duration as highlight.

The explained algorithm will be further improved in the future.

## About guessing contexts

Contexts are hard-coded into the `context.json` file and it requires extensive analysis of the target environments demographics and behaviors to determine them.

As stated in the description, the current contexts are based on Vtuber environment by default, but they can be modified according to your needs, which is explained in [advanced usage](#Advanced-usage) section.

## Advanced usage

WIP

## Possible issues

### It keeps throwing error when reading cached messages

It's most likely caused by an interrupted I/O operation. Try these in order:

- Run the program again with `clear_cache` option on (`--clear-cache` for CLI).

```python
from streamanalyser import streamanalyser as sa

if __name__ == '__main__':
    analyser = sa.StreamAnalyser('Vl_N4AXspo', clear_cache=True)
    analyser.get_messages()
```

or

```bash
python cli.py [stream-id] --clear-cache
```

- Find `src/metadata/[stream-id].yaml` file inside the package location and set `is-complete` option to `False`. Then run the program again with `limit=None`.

- Delete all the cached files by hand in `src/[cache, metadata, thumbnails]`

Should the error persists, please open an issue.

### Can't see Japanese characters in console

Just changing the code page to 932 should work.

```bash
C:\Your\Path> chcp 932
Active code page: 932

C:\Your\Path> 今日本語書ける
```

Use `chcp 65001` to go back. Or simply reopen the CMD.

### Can't see Japanese characters in graph

Download the font [here](https://www.google.com/get/noto/#sans-jpan) and put the `NotoSansCJKjp-regular.otf` file into `src/fonts` folder, so matplotlib can use the font.

## Future goals

- Expand to other stream platforms.

- Automatize context guessing.

- End world hunger.

## License
[GPL v3.0](https://choosealicense.com/licenses/gpl-3.0/)