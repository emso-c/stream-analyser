import streamanalyser as sa
from modules.filehandler import streamanalyser_filehandler


# Find highlights for streams that are cached
if __name__ == "__main__":

    # Another option would be creating an empty StreamAnalyser instance to get the cached ids
    for id in streamanalyser_filehandler.get_cached_ids():
        with sa.StreamAnalyser(id, msglimit=1000) as analyser:
            analyser.analyse()
            analyser.get_highlights(
                top=len(analyser.highlights), output_mode="detailed"
            )
            print(f"Analysed {id} ({analyser.metadata['title']})")
