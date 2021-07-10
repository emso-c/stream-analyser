from StreamAnalyser import StreamAnalyser


# Find users that typed more than one comment
if __name__ == "__main__":
    analyser = StreamAnalyser('pVRvx4FBEwU', limit=1000, verbose=False)
    analyser.analyse()

    for author in analyser.authors:
        # Should use id instead of username for this example,
        # as there might be users with the same name. 
        msg_count = len(analyser.find_user_messages(id=author.id))
        if msg_count > 1:
            print(author.name, msg_count)