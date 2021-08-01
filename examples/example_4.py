import streamanalyser as sa

# Find and open top highlight in the browser
if __name__ == "__main__":
    analyser = sa.StreamAnalyser(
        'pVRvx4FBEwU', msglimit=1000, verbose=True,
        disable_logs=True, not_cache=True
    )

    with analyser:
        analyser.analyse()

        highlights = analyser.print_highlights(top=1)
        for highlight in highlights:
            highlight.open_in_browser("chrome")
        