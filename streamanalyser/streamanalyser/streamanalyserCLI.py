from streamanalyser import streamanalyser as sa
import sys
import os
import argparse

# a basic CLI to fulfill the core features

def parseargs():
    #TODO make args more descriptive and better formatted 
    parser = argparse.ArgumentParser()
    parser.add_argument("id", 
        help="id of the YouTube live stream")
    parser.add_argument("-v", "--verbose",  action="store_true",
        help="make output verbose",)
    parser.add_argument("-l", "--limit", default=None, type=int, 
        help="message limit to fetch")
    parser.add_argument("-t", "--top", default=None, type=int, 
        help="option to return top n highlights.")
    parser.add_argument("-f", "--filter", nargs='+', default=[], 
        help="highlight intensity levels to filter")
    parser.add_argument("-kw", "--keyword-limit", default=4, type=int, 
        help="keyword amount to get for each highlight")
    parser.add_argument("-w", "--window", default=40, type=int, 
        help="window to calculate moving average of message frequency")
    parser.add_argument("-tr", "--thumb-res", default=2, type=int, 
        help="Thumbnail resolution level.\n0 is lowest and 3 is highest")
    parser.add_argument("-s", "--summary", action="store_true", 
        help="print highlight summary")
    parser.add_argument("-hl", "--highlights", action="store_true",
        help="print highlights")
    parser.add_argument("-hlu", "--highlight-urls", action="store_true", 
        help="print highlights in url form")
    parser.add_argument("-g", "--graph", action="store_true",
        help="show graph")
    parser.add_argument("--clear-cache", action="store_true",
        help="clear cache for the particular id before fetching it's messages")
    parser.add_argument('-exp', '--export', nargs='?', const='default', type=str, 
        help="export data to a specified path, leave empty to use the default path")
    parser.add_argument("-efn", "--export-folder-name", default=None, type=str,
        help="sets export folder name")
    parser.add_argument("-fm", "--find-message", type=str,
        help="find messages containing the given phrase")
    parser.add_argument("-e", "--exact", action="store_true", required='--find-message' in sys.argv, 
        help="option for matching phrase to be exactly the same with the message, not only a part it")
    parser.add_argument("-sc", "--strict-case", action="store_true",  required='--find-message' in sys.argv,
        help="option to match the case exactly. must be used with --find-message option")
    parser.add_argument("-fum", "--find-user-messages", action="store_true", 
        help="find messages the specified user made\nmust be used with --user-id or --username")
    user_info = parser.add_mutually_exclusive_group()
    user_info.add_argument("--user-id", default=None, type=str,
        help="id of the user")
    user_info.add_argument("--username", default=None, type=str,
        help="username of the user")
    parser.add_argument("--no-sound", action="store_true",
         help="not make a sound when the program is completed")
    parser.add_argument("--open-in-chrome", action="store_true",
        help="open top highlights in chrome in descending order. must be used with --top and --highlights options",)
    parser.add_argument("--ignore-warnings", action="store_true",
        help="ignore warning messages")
    return parser.parse_args()

def main():
    args = parseargs()
    analyser = sa.StreamAnalyser(
        args.id,
        args.limit,
        args.keyword_limit,
        args.window,
        args.thumb_res,
        args.clear_cache,
        args.ignore_warnings,
        args.verbose
    )
    analyser.analyse()
    
    if args.find_message:
        for msg in analyser.find_messages(args.find_message, args.exact, not args.strict_case):
            print(msg)
    
    if args.find_user_messages:
        for msg in analyser.find_user_messages(args.user_id, args.username):
            print(msg)
    
    if args.summary:
        top_highlights = analyser.print_summary(top=args.top)

    if args.highlights:
        top_highlights = analyser.print_highlights(top=args.top)
    
    if args.highlight_urls:
        top_highlights = analyser.print_urls(top=args.top)

    if args.open_in_chrome and top_highlights:
        for highlight in top_highlights:
            highlight.open_in_chrome()

    if not args.no_sound:
        os.system("echo ") # windows notification sound
    
    if args.export:
        path = None if args.export == 'default' else args.export
        analyser.export_data(path, args.export_folder_name)

    if args.graph:
        analyser.show_graph()

if __name__ == "__main__":
    main()
