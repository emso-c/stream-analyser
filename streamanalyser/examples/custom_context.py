from colorama import Fore
import streamanalyser as sa
import os

# Loading custom context
if __name__ == "__main__":
    analyser_obj = sa.StreamAnalyser(
        "ShB4Wen_HBg",
        verbose=True,
        not_cache=True,
        disable_logs=True,
        msglimit=1000,
        default_context_path=None # set default context path to None to disable premade default contexts
    )
    with analyser_obj as analyser:
        # context source paths should be absolute paths
        analyser.context_source.add(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "contexts_example.json"
        ))

        # context sources should be added before the analyse function
        analyser.analyse()

        analyser.get_highlights(output_mode="detailed")
