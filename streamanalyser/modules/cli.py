import sys
import os
import argparse

import streamanalyser as sa

# a basic CLI to fulfill the core features


def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("id", help="id of the YouTube live stream")
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help="make output silent",
    )
    parser.add_argument(
        "-l", "--limit", default=None, type=int, help="message limit to fetch"
    )
    parser.add_argument(
        "-t", "--top", default=None, type=int, help="option to return top n highlights"
    )
    parser.add_argument(
        "-if",
        "--intensity-filters",
        nargs="+",
        default=[],
        help="highlight intensity levels to filter out",
    )
    parser.add_argument(
        "-kf", "--keyword-filters", nargs="+", default=[], help="keywords to filter out"
    )
    parser.add_argument(
        "-inc",
        "--include-context",
        nargs="+",
        default=[],
        help="keywords to filter out",
    )
    parser.add_argument(
        "-exc",
        "--exclude-context",
        nargs="+",
        default=[],
        help="keywords to filter out",
    )
    parser.add_argument(
        "-kw",
        "--keyword-limit",
        default=4,
        type=int,
        help="keyword amount to get for each highlight",
    )
    parser.add_argument(
        "-w",
        "--window",
        default=30,
        type=int,
        help="window to calculate moving average of message frequency",
    )
    parser.add_argument(
        "-ho",
        "--highlight-output",
        default=None,
        type=str,
        help="print highlights. Options are 'detailed', 'summary' and 'url'",
    )
    parser.add_argument("-g", "--graph", action="store_true", help="show graph")
    parser.add_argument(
        "-sca", "--show-cached", action="store_true", help="show cached file ids"
    )
    parser.add_argument(
        "-exp",
        "--export",
        nargs="?",
        const="default",
        type=str,
        help="export data to a specified path, leave empty to use the default path",
    )
    parser.add_argument(
        "-efn",
        "--export-folder-name",
        default=None,
        type=str,
        help="sets export folder name",
    )
    parser.add_argument(
        "-fm",
        "--find-messages",
        nargs="?",
        const="",
        type=str,
        help="find messages containing the given phrase",
    )
    parser.add_argument(
        "-e",
        "--exact",
        action="store_true",
        required="--find-message" in sys.argv,
        help="option for matching phrase to be exactly the same with the message, not only a part it",
    )
    parser.add_argument(
        "-sc",
        "--strict-case",
        action="store_true",
        required="--find-message" in sys.argv,
        help="option to match the case exactly. must be used with --find-message option",
    )
    parser.add_argument(
        "-fum",
        "--find-user-messages",
        action="store_true",
        help="find messages the specified user made\nmust be used with --user-id or --username",
    )
    user_info = parser.add_mutually_exclusive_group()
    user_info.add_argument("--user-id", default=None, type=str, help="id of the user")
    user_info.add_argument(
        "--username", default=None, type=str, help="username of the user"
    )
    parser.add_argument(
        "-ns",
        "--no-sound",
        action="store_true",
        help="do not make a sound when the program is completed",
    )
    parser.add_argument(
        "--open-in-chrome",
        action="store_true",
        help="open top highlights in chrome in descending order. must be used with --top and --highlights options",
    )
    parser.add_argument(
        "--thumb-res-lvl",
        default=2,
        type=int,
        help="thumbnail resolution level (0-3) with 0 being lowest and 3 being highest",
    )
    parser.add_argument(
        "-dl",
        "--disable-logs",
        action="store_true",
        help="actions done withing the current session will not be logged",
    )
    parser.add_argument(
        "-ld",
        "--log-duration",
        default=15,
        type=int,
        help="how old a log file should be to get deleted (in days)",
    )
    parser.add_argument(
        "-r", "--reset", action="store_true", help="clear cache before analysing"
    )
    parser.add_argument(
        "-nc", "--not-cache", action="store_true", help="clear cache after analysing "
    )
    parser.add_argument(
        "-md",
        "--min-duration",
        default=15,
        type=int,
        help="minimum highlight duration in seconds",
    )
    parser.add_argument(
        "-oef",
        "--open-export-folder",
        action="store_true",
        help="open the export folder in file explorer after exporting",
    )
    parser.add_argument(
        "-wc", "--wordcloud", action="store_true", help="show word cloud"
    )
    parser.add_argument(
        "-wcs", "--wordcloud-scale", default=3, type=int, help="scale of the wordcloud"
    )
    user_info.add_argument(
        "--yt-api-key", default="", type=str, help="youtube api key"
    )
    return parser.parse_args()


def main():
    args = parseargs()

    analyser = sa.StreamAnalyser(
        args.id,
        msglimit=args.limit,
        verbose=not args.silent,
        thumb_res_lvl=args.thumb_res_lvl,
        yt_api_key=args.yt_api_key,
        disable_logs=args.disable_logs,
        log_duration=args.log_duration,
        reset=args.reset,
        not_cache=args.not_cache,
        window=args.window,
        min_duration=args.min_duration,
        keyword_limit=args.keyword_limit,
        keyword_filters=args.keyword_filters,
    )

    with analyser:
        fetched, read, analysed = False, False, False
        def fetch_data():
            nonlocal fetched
            if fetched:
                return
            if not analyser.is_cached:
                analyser.collect_data()
            analyser.enforce_integrity()
            fetched = True
        def read_data():
            fetch_data()
            nonlocal read
            if read:
                return
            analyser.read_data()
            analyser.refine_data()
            analyser.fetch_missing_messages()
            read = True
        def analyse_data():
            read_data()
            print()
            nonlocal analysed
            if analysed:
                return
            analyser.analyse_data()
            analysed = True
        
        # handle arguments
        if args.find_messages=="":
            read_data()
            for msg in analyser.messages:
                print(msg)
        elif args.find_messages:
            read_data()
            for msg in analyser.find_messages(
                args.find_messages, args.exact, not args.strict_case
            ):
                print(msg)

        if args.find_user_messages:
            read_data()
            messages=analyser.find_user_messages(id=args.user_id, username=args.username)
            if not messages:
                print("User not found")
            else:
                for msg in messages:
                    print(msg)

        if args.highlight_output:
            analyse_data()
            top_highlights = analyser.get_highlights(
                top=args.top,
                output_mode=args.highlight_output,
                include=args.include_context,
                exclude=args.exclude_context,
                intensity_filters=args.intensity_filters,
            )

        if args.open_in_chrome and top_highlights:
            analyse_data()
            for highlight in top_highlights:
                highlight.open_in_browser()

        if args.show_cached:
            print(analyser.cached_ids())

        if args.export:
            analyse_data()
            path = None if args.export == "default" else args.export
            analyser.export_data(args.export_folder_name, path, args.open_export_folder)

        if args.graph:
            analyse_data()
            analyser.show_graph()

        if args.wordcloud:
            analyse_data()
            analyser.generate_wordcloud(scale=args.wordcloud_scale).to_image().show()

        if not args.no_sound:
            os.system("echo ")  # windows notification sound


if __name__ == "__main__":
    main()
