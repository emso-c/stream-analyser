import streamanalyser as sa

# Find highlights for streams that are cached
if __name__ == "__main__":

    # Limited to merely 1000 messages for this example as it'd take way longer to fetch all messages.
    message_limit = 1000

    # Another option would be creating an empty StreamAnalyser instance to get the cached ids
    for id in sa.StreamAnalyser("").filehandler.get_cached_ids():
        with sa.StreamAnalyser(id, msglimit=message_limit) as analyser:
            analyser.analyse()
            analyser.get_highlights(
                top=len(analyser.highlights), output_mode="detailed"
            )
            print(f"Analysed {id} ({analyser.metadata['title']})")
