from colorama import Fore
import streamanalyser as sa


# Customize intensity options
if __name__ == "__main__":
    analyser_obj = sa.StreamAnalyser(
        "ShB4Wen_HBg",
        verbose=True,
        not_cache=True,
        disable_logs=True,
        msglimit=5000,
        intensity_levels=["LOW", "MEDIUM", "HIGH"],
        intensity_constants=[0, 1, 2],
        intensity_colors=[Fore.YELLOW, Fore.RED, Fore.MAGENTA],
    )
    with analyser_obj as analyser:
        analyser.analyse()
        analyser.get_highlights(output_mode="summary")
