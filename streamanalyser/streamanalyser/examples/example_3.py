from StreamAnalyser import StreamAnalyser


# Find instances of a specified message that has been written by the same user.
if __name__ == "__main__":
    analyser = StreamAnalyser('pVRvx4FBEwU', limit=10000, verbose=False)
    analyser.analyse()

    message_to_search = 'うん'
    user_id = 'UChh460hgxJ9AwB0mnlu__Cg'

    def solution1():
        msgs = []
        for msg in analyser.find_messages(message_to_search, exact=True, ignore_case=False):
            if msg.author.id == user_id:
                msgs.append(msg)
        return msgs

    def solution2():
        msgs = []
        for msg in analyser.find_user_messages(id=user_id):
            if msg.text == message_to_search:
                msgs.append(msg)
        return msgs

    print("Solution 1")
    [print(msg) for msg in solution1()]
    print("\nSolution 2")
    [print(msg) for msg in solution2()]


    