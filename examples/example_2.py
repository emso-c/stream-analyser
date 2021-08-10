import streamanalyser as sa


# Find users that typed more than one comment
if __name__ == "__main__":
    analyser = sa.StreamAnalyser(
        "pVRvx4FBEwU", msglimit=1000, verbose=True, disable_logs=True, not_cache=True
    )

    with analyser:
        analyser.collect_data()
        analyser.read_data()
        analyser.refine_data()

        for author in analyser.authors:
            # Should use id instead of username for this example,
            # as there might be users with the same name.
            msg_count = len(analyser.find_user_messages(id=author.id))
            if msg_count > 1:
                print(author.name, msg_count)
