import streamanalyser as sa

# Find instances of a specified message that has been written by the same user.
if __name__ == "__main__":
    analyser = sa.StreamAnalyser(
        "pVRvx4FBEwU", msglimit=1000, verbose=True, disable_logs=True, not_cache=True
    )

    with analyser:
        analyser.collect_data()
        analyser.read_data()
        analyser.refine_data()

        message_to_search = ":_koroneIiyubi::_koroneIiyubi::_koroneIiyubi:"
        user_name = "Rarely Spotted"

        def solution1():
            found_messages = analyser.find_messages(
                message_to_search,
                exact=True,
                ignore_case=False,
            )
            for msg in found_messages:
                if msg.author.name == user_name:
                    yield msg

        def solution2():
            for msg in analyser.find_user_messages(username=user_name):
                if msg.text == message_to_search:
                    yield msg

        print("Solution 1")
        [print(msg) for msg in solution1()]
        print("\nSolution 2")
        [print(msg) for msg in solution2()]
