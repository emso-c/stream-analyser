import streamanalyser as sa

# Set a custom storage path
if __name__ == "__main__":
    analyser_obj = sa.StreamAnalyser(
        "pVRvx4FBEwU",
        verbose=True,
        disable_logs=True,
        not_cache=True,
        msglimit=100,
        storage_path="C:\\Stream_Analyser_Example_Custom_Storage"
    )
    with analyser_obj as analyser:
        analyser.analyse()
        analyser.get_highlights(output_mode="detailed")
        analyser.open_cache_folder()