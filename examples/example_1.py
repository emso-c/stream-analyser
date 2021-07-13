from StreamAnalyser import StreamAnalyser


# Get n most frequently used words with a recursive approach
if __name__ == "__main__":
    analyser = StreamAnalyser('pVRvx4FBEwU', limit=1000, verbose=False)
    analyser.analyse()

    n = 6
    mfuw = []
    for _ in range(n):
        mfuw.append(analyser.most_used_word(exclude=mfuw)[0])
    
    for item in mfuw:
        print(item)