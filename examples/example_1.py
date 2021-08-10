import streamanalyser as sa


# Get n most frequently used words with a recursive approach
if __name__ == "__main__":
    analyser = sa.StreamAnalyser(
        "pVRvx4FBEwU", msglimit=1000, verbose=True, disable_logs=True, not_cache=True
    )

    with analyser:
        analyser.collect_data()
        analyser.read_data()
        analyser.refine_data()

        n = 6
        mfup = []
        while n:
            mfup.append(analyser.most_used_phrase(exclude=mfup)[0])
            n -= 1

        for item in mfup:
            print(item)
