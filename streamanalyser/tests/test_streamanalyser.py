import json
import shutil
import unittest
import warnings
import os
import importlib

import sys
if __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.structures import Author, Message
from streamanalyser import streamanalyser as sa 

class TestStreamAnalyser(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", category=ResourceWarning)

    def tearDown(self):
        # clear caches of used id's
        for id in ["testid", "um196SMIoR8"]:
            with sa.StreamAnalyser(id, 0, disable_logs=True) as analyser:
                analyser.clear_cache()

    def test_cache_messages(self):
        with sa.StreamAnalyser("testid", 1, disable_logs=True) as analyser:
            analyser._cache_messages([{}])
            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        analyser.filehandler.sid_path,
                        analyser.filehandler.message_fname + ".gz",
                    )
                )
            )

    def test_cache_metadata(self):
        with sa.StreamAnalyser("testid", 1, disable_logs=True) as analyser:
            analyser._cache_metadata({})

            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        analyser.filehandler.sid_path,
                        analyser.filehandler.metadata_fname,
                    )
                )
            )

    def test_collect_read_data(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.collect_data()
            analyser.read_data()
            self.assertTrue(
                analyser._raw_messages[0]["author"]["id"], "UCX07ffYvacTkgo89MjNpweg"
            )
            self.assertTrue(
                analyser.metadata["title"],
                "【APEX】英語…頑張ります！！\u3000w/" + " Roboco,Amelia【常闇トワ/ホロライブ】",
            )

    @unittest.skip("Fix later. Refactor sample messages.")
    def test_refine_data(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser._raw_messages = sample_raw_messages
            analyser.refine_data()
            self.assertEqual(analyser.messages[0].text, "kon...")
            self.assertEqual(analyser.authors[0].id, "UCX07ffYvacTkgo89MjNpweg")

    @unittest.skip("Fix later. Refactor sample messages.")
    def test_analyse_data(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.messages = analyser.refiner.refine_raw_messages(
                sample_raw_messages
            )
            analyser.metadata = {"title": "test"}
            analyser.analyse_data()

            self.assertEqual(
                analyser.highlights[0].colorless_str,
                "[0:00:01] greeting: こんやっぴートワ様いえーい, こん, こん…, "
                + "kon (24 messages, high intensity, 1.042 diff, 19s duration)",
            )

    @unittest.skipIf(
        importlib.util.find_spec("not_a_module") is None,
        "WordCloud module is not installed",
    )
    def test_generate_wordcloud(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.messages = analyser.refiner.refine_raw_messages(
                sample_raw_messages
            )
            self.assertTrue(analyser.generate_wordcloud(scale=0.1).to_image())

    def test_find_messages(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.messages = [Message(
                id=raw_message["message_id"],
                text=raw_message["message"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"],
                ),
            ) for raw_message in sample_raw_messages]

            self.assertEqual(
                analyser.find_messages("こんやっぴ~")[0].colorless_str,
                "[0:00:39] Yuzuchu: こんやっぴ~",
            )

            # ignore_case should produce different results
            self.assertNotEqual(
                analyser.find_messages("kon...", ignore_case=False),
                analyser.find_messages("kon...", ignore_case=True),
            )

            # It should return empty list when exact is set
            # even though there's "kon" in other messages
            self.assertEqual(analyser.find_messages("kon", exact=True), [])

    def test_find_user_messages(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.messages = [Message(
                id=raw_message["message_id"],
                text=raw_message["message"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"],
                ),
            ) for raw_message in sample_raw_messages]

            self.assertEqual(len(analyser.find_user_messages(username="Yuzuchu")), 2)

            self.assertEqual(
                len(analyser.find_user_messages(id="UCBLOc9HL4kIvp36bMqu7pxg")), 1
            )

    def test_most_used_phrase(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.messages = [Message(
                id=raw_message["message_id"],
                text=raw_message["message"],
                time=round(raw_message["time_in_seconds"]),
                author=Author(
                    id=raw_message["author"]["id"],
                    name=raw_message["author"]["name"],
                ),
            ) for raw_message in sample_raw_messages]

            self.assertEqual(analyser.most_used_phrase(), ("こんやっぴートワ様いえーい", 35))

            # with not normalize
            self.assertEqual(
                analyser.most_used_phrase(normalize=False), ("こん:_やっぴー::_トワ様いえーい:", 35)
            )

            # with exclude
            self.assertEqual(
                analyser.most_used_phrase(
                    exclude=["こんやっぴートワ様いえーい"],
                ),
                ("konyappi", 11),
            )

            # with exclude and not normalize
            self.assertEqual(
                analyser.most_used_phrase(
                    exclude=["こん:_やっぴー::_トワ様いえーい:"], normalize=False
                ),
                ("こん...", 6),
            )

    def test_analyse(self):
        src_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),  "custom_context.json"
        )
        with open(src_path, "w", encoding="utf-8") as file:
            file.write(json.dumps([
                {
                    "reaction_to": "greeting",
                    "triggers": [
                        {
                            "phrase": "こん :_やっぴー::_トワ様いえーい:",
                            "is_exact": True
                        },
                        {
                            "phrase": "konyappi",
                            "is_exact": False
                        },
                    ]
                }], indent=4
            ))
        # BUG: fix keyword limit error (set keyword limit to 10 to reproduce)
        with sa.StreamAnalyser("um196SMIoR8", 100, disable_logs=True, keyword_limit=10, default_context_path=None) as analyser:
            analyser.context_source.add(src_path)
            analyser.analyse()
            self.assertEqual(analyser.highlights[0].contexts, {"greeting"})

            os.remove(src_path)

    def test_check_integrity(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.collect_data()

            # intentionally delete metadata file
            analyser.filehandler.delete_file(
                os.path.join(
                    analyser.filehandler.sid_path, analyser.filehandler.metadata_fname
                )
            )

            # create unnecessary dummy file
            with open(analyser.filehandler.sid_path + "\\dummy.txt", "w"):
                pass

            missing_files, unnecessary_files = analyser.filehandler.check_integrity()

            # should detect metadata as missing file
            self.assertEqual(missing_files, [analyser.filehandler.metadata_fname])

            # should detect dummy.txt as unnecessary file
            self.assertEqual(unnecessary_files, ["dummy.txt"])

            # intentionally decompress message file
            analyser.filehandler._decompress_file(
                os.path.join(
                    analyser.filehandler.sid_path, analyser.filehandler.message_fname
                )
            )

            # try again with autofix
            missing_files, unnecessary_files = analyser.filehandler.check_integrity(
                autofix=True
            )

            # still should detect metadata as missing file,
            # but decompressed file should be compressed
            self.assertEqual(missing_files, [analyser.filehandler.metadata_fname])
            # should delete dummy file
            self.assertEqual(unnecessary_files, [])

    def test_enforce_integrity(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            analyser.collect_data()

            # intentionally delete cache files
            analyser.clear_cache(delete_root_folder=False)

            # create unnecessary dummy file
            with open(analyser.filehandler.sid_path + "\\dummy.txt", "w+") as f:
                pass

            # call the function
            analyser.enforce_integrity()

            # check integrity now
            missing_files, unnecessary_files = analyser.filehandler.check_integrity()

            self.assertEqual(missing_files, [])
            self.assertEqual(unnecessary_files, [])

    @unittest.skipIf(
        importlib.util.find_spec("not_a_module") is None,
        "WordCloud module is not installed",
    )
    def test_export(self):
        with sa.StreamAnalyser("um196SMIoR8", 1, disable_logs=True) as analyser:
            msg_path = os.path.join(
                analyser.filehandler.sid_path,
                analyser.filehandler.message_fname + ".gz",
            )
            mdata_pth = os.path.join(
                analyser.filehandler.sid_path,
                analyser.filehandler.metadata_fname,
            )

            analyser._raw_messages = sample_raw_messages
            analyser.refine_data()
            analyser.highlights = [
                sa.structures.Highlight(
                    "testid",
                    0,
                    10,
                    sa.structures.Intensity("lvl", 2, sa.structures.AnsiFore.GREEN),
                    5,
                    analyser.messages,
                    ["kword"],
                    ["contxt"],
                )
            ]

            with open(msg_path, "w"):
                pass
            with open(mdata_pth, "w"):
                pass

            analyser.export_data(folder_name="test235234")
            test_export_folder = os.path.join(
                analyser.filehandler.export_path, "test235234"
            )
            fnames = analyser.filehandler.get_filenames(test_export_folder)
            cheklist = ["highlights", "messages", "metadata", "thumbnail", "wordcloud"]
            for item in cheklist:
                self.assertTrue(item in fnames)

            shutil.rmtree(test_export_folder)

    def test_fetch_missing_messages(self):
        with sa.StreamAnalyser("um196SMIoR8", 2, disable_logs=True) as analyser:
            analyser.collect_data()
            analyser.read_data()
            analyser.refine_data()

            # increase message limit (inital was 2)
            analyser.msglimit = 4

            # call the function
            analyser.fetch_missing_messages()

            # the missing 2 should be fetched and refined
            self.assertEqual(len(analyser.messages), 4)

            # set is-complete to True manually
            # (it's set to true by itself when msg_limit is None in practice)
            analyser.update_metadata({"is-complete": True})

            # increase message limit again
            analyser.msglimit = 8

            # call the function
            analyser.fetch_missing_messages()

            # the messages should NOT be fetched as is-complete is `True`
            self.assertEqual(len(analyser.messages), 4)

    @unittest.skip(
        "This test is always skipped for now as it clears existing cache. Gonna fix it later"
    )
    def test_cache_options(self):
        with sa.StreamAnalyser(
            "testid", 0, cache_limit=10, disable_logs=False
        ) as analyser:
            # create dummy files in the cache folder
            # and pass cache limit intentionally
            msg_path = os.path.join(
                analyser.filehandler.cache_path,
                "testid",
                analyser.filehandler.message_fname + ".gz",
            )
            with open(msg_path, "w"):
                pass
            for i in range(analyser.cache_limit):
                analyser.filehandler.create_dir_if_not_exists(
                    os.path.join(
                        analyser.filehandler.cache_path,
                        "testid" + str(i),
                    )
                )
            msg_path = os.path.join(
                analyser.filehandler.cache_path,
                "testid" + str(i),
                analyser.filehandler.message_fname + ".gz",
            )
            with open(msg_path, "w"):
                pass

        with sa.StreamAnalyser(
            "testid",
            0,
            disable_logs=False,
            cache_limit=10,
            cache_deletion_algorithm="mru",
        ) as analyser:
            # most recently created folder must have been deleted
            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        analyser.filehandler.cache_path,
                        "testid" + str(analyser.cache_limit - 1),
                    )
                )
            )

        with sa.StreamAnalyser(
            "testid",
            0,
            disable_logs=False,
            cache_limit=9,
            cache_deletion_algorithm="fifo",
        ) as analyser:
            # least recently created folder must have been deleted
            self.assertFalse(
                os.path.exists(os.path.join(analyser.filehandler.cache_path, "testid0"))
            )

        with sa.StreamAnalyser(
            "testid",
            0,
            disable_logs=False,
            cache_limit=8,
            cache_deletion_algorithm="lru",
        ) as analyser:
            # least recently created folder must have been deleted
            self.assertFalse(
                os.path.exists(os.path.join(analyser.filehandler.cache_path, "testid1"))
            )

sample_raw_messages = [
    {
        "author": {"id": "UCX07ffYvacTkgo89MjNpweg", "name": "RathalosRE"},
        "message_type": "text_message",
        "message": "kon...",
        "message_id": "CjkKGkNMSHU0ZmpxNl9FQ0ZjTWZmUW9kWlJzSXFBEhtDSlRCd0szbTZfRUNGY2ZGeEFvZHVVUUEwZzA%3D",
        "time_in_seconds": 0,
    },
    {
        "author": {"id": "UClaAJUb11yYCjY5PdhZmfsg", "name": "rubin"},
        "message_type": "text_message",
        "message": ":_トワ文字:iting:_トワ様いえーい:",
        "message_id": "CjkKGkNObWgtX2pxNl9FQ0ZZVVo1d29keGl3SlBREhtDTTZqcnVqcTZfRUNGY2VBWXdZZC1HSU5jdzA%3D",
        "time_in_seconds": 0,
    },
    {
        "author": {"id": "UCApQ-9DiTSIeqTZWXMXzR8g", "name": "Lucas Barreto"},
        "message_type": "text_message",
        "message": "こん。。。",
        "message_id": "CkUKGkNLN1g0UHZxNl9FQ0ZWb1ByUVlkVFg4RHVBEidDSmlENl9mcTZfRUNGWWlKbVFvZHNOOEwxQTE2MjY1ODQzNjgwNzU%3D",
        "time_in_seconds": 2.042,
    },
    {
        "author": {"id": "UCBLOc9HL4kIvp36bMqu7pxg", "name": "Rena Moon"},
        "message_type": "text_message",
        "message": "こん",
        "message_id": "CjkKGkNPcmVtZnpxNl9FQ0ZhbkZ3UW9kem4wQ1pREhtDSlBaLUpqcDZfRUNGWVhaMVFvZFJCc0FxZzA%3D",
        "time_in_seconds": 4.126,
    },
    {
        "author": {"id": "UCK89HIgAk_WVwbl8dySd1ng", "name": "Prince Chips"},
        "message_type": "text_message",
        "message": ":_トワ文字:aiting!",
        "message_id": "CjkKGkNQZXh6ZnpxNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDT0Npel9YcTZfRUNGUVZUV0FvZHJZRUYzdzA%3D",
        "time_in_seconds": 5.334,
    },
    {
        "author": {"id": "UCyesjldaXmoLOKRoBaekf_w", "name": "Chewyboot "},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CjkKGkNPYXJsZjNxNl9FQ0ZZRVhmUW9kWHY4SU53EhtDSm1qX3VUTDZfRUNGYllUclFZZEZiNEhVQTE%3D",
        "time_in_seconds": 6.414,
    },
    {
        "author": {"id": "UCm3PZqgUsSa5t4X_KU8JLLQ", "name": "Silence voice"},
        "message_type": "text_message",
        "message": "kon...",
        "message_id": "CjkKGkNOUzM0ZjNxNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDTHZVamZmazZfRUNGZDBMdHdBZGhqc0lYUTE%3D",
        "time_in_seconds": 7.262,
    },
    {
        "author": {"id": "UCRGu8LiQgoN3rSaSGAFWHlg", "name": "kurobear"},
        "message_type": "text_message",
        "message": "こん....",
        "message_id": "CjkKGkNMRHU3ZjNxNl9FQ0ZkZ0FyUVlkdVBRRlFREhtDTlB6d3ZYcTZfRUNGYWRSaFFvZENKc0czZzA%3D",
        "time_in_seconds": 7.405,
    },
    {
        "author": {"id": "UCuPkyqDfoIHYl-sSfhdDtDw", "name": "Yuzuchu"},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CkUKGkNPaUNtZjdxNl9FQ0ZkZ0FyUVlkdVBRRlFREidDTU9vekxfcTZfRUNGZWJEd2dRZGpiY0k4dzE2MjY1ODQzNzM4MDM%3D",
        "time_in_seconds": 8.207,
    },
    {
        "author": {"id": "UCb6Kbp7NtVgeSD9a9DCz1nQ", "name": "Yumina"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CjkKGkNOQzctdjdxNl9FQ0ZSd2RyUVlkb25FQnR3EhtDSUdNM01mbzZfRUNGYlNybFFJZHg4QUhYdzE%3D",
        "time_in_seconds": 10.182,
    },
    {
        "author": {"id": "UCw6g9yBkt54jUJI6elkdZzg", "name": "Khoa Nguyễn Văn"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CkUKGkNMT0tydl9xNl9FQ0ZjTWZmUW9kWlJzSXFBEidDUDNaMGZ2cTZfRUNGWHRTaFFvZGhNQUYwQTE2MjY1ODQzNzQxNzk%3D",
        "time_in_seconds": 11.014,
    },
    {
        "author": {"id": "UCojDEDgA2-m632NaR29vNdQ", "name": "XxKawaiixRicexX"},
        "message_type": "text_message",
        "message": "Welcome to the family:_トワ様いえーい:",
        "message_id": "CjkKGkNJR1Rzdl9xNl9FQ0ZkZ0FyUVlkdVBRRlFREhtDTGZWcEpqcDZfRUNGWXlpeEFvZE56b1AxUTA%3D",
        "time_in_seconds": 11.051,
    },
    {
        "author": {"id": "UCgTvHUoeeF8z_pFqbr8e26w", "name": "mayt_ S."},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNQRC1sSURyNl9FQ0ZjX0N3Z1FkUHl3RnRREidDT2lpbXZ2cTZfRUNGYm5BT0FZZGhZQU5uUTE2MjY1ODQzNzY4ODE%3D",
        "time_in_seconds": 12.797,
    },
    {
        "author": {"id": "UCx4WCmY3Z09P9383-W49yig", "name": "如月白兎"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNPUDJ5WURyNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDTFA3czdmZjZfRUNGZWxDOVFVZHR1UUh5ZzI%3D",
        "time_in_seconds": 13.564,
    },
    {
        "author": {"id": "UCLeLH-PQA2ADFOW1AorGUZw", "name": "Hannah Althea"},
        "message_type": "text_message",
        "message": "Kon....",
        "message_id": "CjkKGkNNYTdob0hyNl9FQ0ZjX0N3Z1FkUHl3RnRREhtDTWI3OF96cTZfRUNGVU5IaFFvZFRBVUdydzA%3D",
        "time_in_seconds": 14.211,
    },
    {
        "author": {"id": "UCSTO1VvCNyHoMoEQhScEJIw", "name": "Raseru Kiiro"},
        "message_type": "text_message",
        "message": "Konyappi !",
        "message_id": "CjkKGkNMYkFrSUhyNl9FQ0ZaRU5yUVlkQ0I4UEpnEhtDS0dreDR2VDZfRUNGWW9rV0FvZFdLWUxWUTA%3D",
        "time_in_seconds": 14.32,
    },
    {
        "author": {"id": "UCp5N3jaxHlMq-Vu7OLJOJ9A", "name": "Rain_sw ⁸⁰れいん"},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CjoKGkNNMjl5NEhyNl9FQ0ZWb1ByUVlkVFg4RHVBEhxDUHJjN0lqbzZfRUNGY1hWVEFJZFVad0xKUS0x",
        "time_in_seconds": 15.766,
    },
    {
        "author": {"id": "UCX07ffYvacTkgo89MjNpweg", "name": "RathalosRE"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNNdlQxb0hyNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDSlRCd0szbTZfRUNGY2ZGeEFvZHVVUUEwZzE%3D",
        "time_in_seconds": 15.902,
    },
    {
        "author": {"id": "UCpHWyGyWROHCbaKna0AdWsg", "name": "Big On Mars"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNJR2g5NEhyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDTm1lNEtmcTZfRUNGUnVKeEFvZGRLUUU2ZzE%3D",
        "time_in_seconds": 16.389,
    },
    {
        "author": {"id": "UCtSNv6VgO9Wx7YN8yqlbnMg", "name": "miha 398"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CjoKGkNMN2JvNExyNl9FQ0ZjTWZmUW9kWlJzSXFBEhxDSmItNGVYcTZfRUNGUUx4T0FZZEhINE1CQS0y",
        "time_in_seconds": 17.228,
    },
    {
        "author": {"id": "UCZ0TEGOiLpOZOAOxA_nRmXw", "name": "きっき"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNJT0J1WUxyNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDTERHMi1ETDZfRUNGUlN4V0FvZHd0RUVhQTE%3D",
        "time_in_seconds": 17.444,
    },
    {
        "author": {"id": "UCo7o-Ib_3NMyNAU-062vN2A", "name": "Old Can"},
        "message_type": "text_message",
        "message": "KONYAPPI",
        "message_id": "CjkKGkNOTzIxSUxyNl9FQ0ZZRVhmUW9kWHY4SU53EhtDT3lialBmcTZfRUNGZGxSWUFvZHZoRU9sZzE%3D",
        "time_in_seconds": 17.965,
    },
    {
        "author": {"id": "UCNDoIL08saEOTZqshRDbOwQ", "name": "ゆきにゃん"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CjoKGkNKcmEzNExyNl9FQ0ZkZ0FyUVlkdVBRRlFREhxDT3pNLV9fcTZfRUNGYWRDaFFvZFBqd01Xdy0w",
        "time_in_seconds": 18.157,
    },
    {
        "author": {"id": "UCiuFMPV1e-fgacO5-uRIwmg", "name": "OMEGAエイキ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNQTGc1b0xyNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDTWJ1MzY3cTZfRUNGVlFGV0FvZExka09UQTE%3D",
        "time_in_seconds": 18.187,
    },
    {
        "author": {"id": "UC61Dme0yj5Y_zd7j1YmFsVQ", "name": "てってれけ"},
        "message_type": "text_message",
        "message": "こんやっぴ～",
        "message_id": "CjkKGkNQT0w2SUxyNl9FQ0ZaTTFyUVlkRTVvRnRBEhtDTDZNbE5IVTZfRUNGWWhZWUFvZEFZc0RwZzA%3D",
        "time_in_seconds": 18.315,
    },
    {
        "author": {"id": "UCyesjldaXmoLOKRoBaekf_w", "name": "Chewyboot"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNLbk1xWVByNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDSm1qX3VUTDZfRUNGYllUclFZZEZiNEhVQTI%3D",
        "time_in_seconds": 19.355,
    },
    {
        "author": {"id": "UC2GrTQsYbNO2T10jgs7qMZg", "name": "Michael Rowland"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNQZjUyb1ByNl9FQ0ZST2JnZ29kMFU4T3hnEhtDUGlTb29YWjZfRUNGWVdvbkFvZEVkZ0xUdzE%3D",
        "time_in_seconds": 20.226,
    },
    {
        "author": {"id": "UCmVWpWJQWmdneqUHIIu2lgw", "name": "JULIAN HERMES 276"},
        "message_type": "text_message",
        "message": "konyappi",
        "message_id": "CkUKGkNOS0lpb1RyNl9FQ0ZlQU5yUVlkMTJrS1FBEidDUFNmcklIcjZfRUNGWGpKY3dFZEdySUcwQTE2MjY1ODQzODQ1ODE%3D",
        "time_in_seconds": 21.06,
    },
    {
        "author": {"id": "UCZZCqNj8D-sttddThLZivUA", "name": "Jimmy Axe"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNPZVVtWVRyNl9FQ0ZZRVhmUW9kWHY4SU53EidDS2VVNm9EcjZfRUNGWXN6S2dvZHBfRURuQTE2MjY1ODQzODUxMjk%3D",
        "time_in_seconds": 21.119,
    },
    {
        "author": {"id": "UCefjOmhflYyZdhU_UHFbqOg", "name": "LetDownLad"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNOVG9ub1RyNl9FQ0ZWb1ByUVlkVFg4RHVBEidDTXZaNG9IcjZfRUNGUVFPclFZZHpIa0NlZzE2MjY1ODQzODQ2NjM%3D",
        "time_in_seconds": 21.233,
    },
    {
        "author": {"id": "UCBJSteJ5LvA8mxoRj0hb_QQ", "name": "avie"},
        "message_type": "text_message",
        "message": "konyappi",
        "message_id": "CkUKGkNManF5b1RyNl9FQ0ZaTTFyUVlkRTVvRnRBEidDS0xmNjREcjZfRUNGYWZhY3dFZHhpc0daUTE2MjY1ODQzODU2MTc%3D",
        "time_in_seconds": 21.942,
    },
    {
        "author": {"id": "UC4ocycPs14eBRTDKC-ZM7kA", "name": "Hololive World"},
        "message_type": "text_message",
        "message": "Hi",
        "message_id": "CkUKGkNKTDV5SVRyNl9FQ0ZlQU5yUVlkMTJrS1FBEidDSzJ3aW9QcjZfRUNGVlRLeEFvZEhpUURVQTE2MjY1ODQzODU3MTk%3D",
        "time_in_seconds": 21.957,
    },
    {
        "author": {"id": "UCsNn93pMaxPR8X7cFtvwZ8g", "name": "Jeje Rndnw"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNJNi15b1RyNl9FQ0ZZRVhmUW9kWHY4SU53EhtDSzJzN0x2YzZfRUNGUkxnY3dFZFV6MElSZzE%3D",
        "time_in_seconds": 22.008,
    },
    {
        "author": {"id": "UCxUSC7aLHt86aMkMUbkgI1g", "name": "Asanya"},
        "message_type": "text_message",
        "message": "こん。。。",
        "message_id": "CkUKGkNORDV5NFRyNl9FQ0ZZbUt3UW9ka1NNRXpREidDTWpLNGYzcTZfRUNGWm1YVVFvZDFKc0xIQTE2MjY1ODQzODg1NjI%3D",
        "time_in_seconds": 22.042,
    },
    {
        "author": {"id": "UCjxi9NW5768uhHAPhdjVW7g", "name": "ソリダス・スネーク"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNKbU1nSVhyNl9FQ0ZjVU5yUVlkQnlZQ3BREhtDTWlUcWJiWjZfRUNGWGhXaFFvZDZCVUwzdzE%3D",
        "time_in_seconds": 22.907,
    },
    {
        "author": {"id": "UCOlCkAoREDtM5JtpKdz8iyQ", "name": "Epuration"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNQcnl3WVhyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDT2ZyeF83bzZfRUNGVk1VZlFvZHhSVU0zZzE%3D",
        "time_in_seconds": 23.958,
    },
    {
        "author": {"id": "UCqbDXM6JwWc2raPEHW4hqCQ", "name": "カズユキ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNJLXp6SVhyNl9FQ0ZkZ0FyUVlkdVBRRlFREidDTWk5cl83cTZfRUNGYmYtT0FZZGFCMEljZzE2MjY1ODQzODk1MzQ%3D",
        "time_in_seconds": 24.031,
    },
    {
        "author": {"id": "UCQ7IlLZ2xLtH5MBZe2jqu3w", "name": "ゆっくりゆあめ"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CkUKGkNQX3ExNFhyNl9FQ0ZjX0N3Z1FkUHl3RnRREidDSkM3X3ZfcTZfRUNGUmd3WUFvZGluVUJXUTE2MjY1ODQzODc0MzQ%3D",
        "time_in_seconds": 24.231,
    },
    {
        "author": {"id": "UCwFklj_pbj0vOxkMev02I4A", "name": "Zheng Xuan Lim"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNQSzc4NFhyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDSjNyczdIYjZfRUNGVXFnNlFvZG5Da09WdzE%3D",
        "time_in_seconds": 24.736,
    },
    {
        "author": {"id": "UCzH8uSW84hwa79oH6Kigaig", "name": "ヴィラガグレン"},
        "message_type": "text_message",
        "message": "こんやっぴ～",
        "message_id": "CjkKGkNNLVZfb1hyNl9FQ0ZjTWZmUW9kWlJzSXFBEhtDTm1Kc09IVTZfRUNGWlJIaFFvZEttWUhiUTE%3D",
        "time_in_seconds": 25.038,
    },
    {
        "author": {"id": "UCINfAMONpumYpwDBFY5ekjw", "name": "しょーにゅー"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNNci1pb2JyNl9FQ0ZSd2RyUVlkb25FQnR3EhtDT2FEN1BQcDZfRUNGVUxqVEFJZHE1SU9XZzI%3D",
        "time_in_seconds": 25.128,
    },
    {
        "author": {"id": "UCqQxu2t-O2kqtPKy54Oz7Qg", "name": "JH"},
        "message_type": "text_message",
        "message": "🎶",
        "message_id": "CjkKGkNQN3NpWWJyNl9FQ0ZaTTFyUVlkRTVvRnRBEhtDSlNoNmV6cTZfRUNGUnhKVEFnZFYtOEMzQTA%3D",
        "time_in_seconds": 25.156,
    },
    {
        "author": {"id": "UC-GyPOPmWcOYUIDd_OYtXCA", "name": "Jajammy RXGD"},
        "message_type": "text_message",
        "message": "konyappi!",
        "message_id": "CkUKGkNPenBub2JyNl9FQ0ZjVU5yUVlkQnlZQ3BREidDTzJjZ29McjZfRUNGYm5MVEFJZDFuQU9OQTE2MjY1ODQzODY3MDI%3D",
        "time_in_seconds": 25.495,
    },
    {
        "author": {"id": "UCLqvMB03DmAEBl4G8qzymhQ", "name": "氷翠"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNQYmtyb2JyNl9FQ0ZWb1ByUVlkVFg4RHVBEidDT0x4NjRMcjZfRUNGVTVFOVFVZHNZQUpYZzE2MjY1ODQzODkzOTc%3D",
        "time_in_seconds": 25.788,
    },
    {
        "author": {"id": "UCatjAKjmySNRrVYvri1bIng", "name": "Nachtflut"},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CkUKGkNNRGl0NGJyNl9FQ0ZRN2F3UW9kb0dJQXFREidDT1hNc2NqcTZfRUNGUWZhVlFvZENxd0FmZzE2MjY1ODQzOTE2OTI%3D",
        "time_in_seconds": 25.993,
    },
    {
        "author": {"id": "UCFqD6L3nhesaQtRmqt_s6aA", "name": "Winks 8"},
        "message_type": "text_message",
        "message": "Kon…",
        "message_id": "CjoKGkNJS1kxb2JyNl9FQ0ZaTTFyUVlkRTVvRnRBEhxDTlRjLTRIcjZfRUNGUm5zT0FZZDZISURhdy0w",
        "time_in_seconds": 26.387,
    },
    {
        "author": {"id": "UC6iKIVMw_zuQWpvAHOyioRA", "name": "いつでも甘いものが食べたい"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNPdU0zWWJyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDSnVtcHFQYjZfRUNGUUhXVEFJZHZQVUNSQTA%3D",
        "time_in_seconds": 26.408,
    },
    {
        "author": {"id": "UCJYmnUdNODP6oDn9FDLkIvQ", "name": "Nekomusume"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNJU24yNGJyNl9FQ0ZjVU5yUVlkQnlZQ3BREidDS19PaTRQcjZfRUNGZHdWWUFvZHJERUFHUTE2MjY1ODQzOTA4NDA%3D",
        "time_in_seconds": 26.409,
    },
    {
        "author": {"id": "UC9l04tt9qHc9tw65pjPJgvQ", "name": "Alterchemist"},
        "message_type": "text_message",
        "message": ":_トワ様いえーい::_トワ様いえーい::_トワ様いえーい:",
        "message_id": "CjkKGkNMZVMzNGJyNl9FQ0ZRcUp3UW9kajI0QjBBEhtDTTZILTdUaDZfRUNGVUVFWlFvZHdKVUw3QTE%3D",
        "time_in_seconds": 26.576,
    },
    {
        "author": {"id": "UCTd2o7B6znKsv_iVAbrQSRA", "name": "upa Upa"},
        "message_type": "text_message",
        "message": "こんやっぴ～",
        "message_id": "CjkKGkNQZTc3SWJyNl9FQ0ZZVVo1d29keGl3SlBREhtDSTM1cklfUzZfRUNGYzB2WUFvZGlVa0ZwZzA%3D",
        "time_in_seconds": 26.657,
    },
    {
        "author": {"id": "UCjsVbOmWfGDv_p4Ju0lJ54w", "name": "Ksha"},
        "message_type": "text_message",
        "message": "konyappi!",
        "message_id": "CjkKGkNQamw4NGJyNl9FQ0ZjX0N3Z1FkUHl3RnRREhtDTmJaeGNfcTZfRUNGYVV6dHdBZHE0NE5YZzA%3D",
        "time_in_seconds": 26.816,
    },
    {
        "author": {"id": "UCt_Cqg78Dg3Lj70vkEytmkA", "name": "Luis de vera"},
        "message_type": "text_message",
        "message": "Konyappi",
        "message_id": "CkUKGkNKNzktSWJyNl9FQ0ZZRVhmUW9kWHY4SU53EidDSWZuMzRIcjZfRUNGVTYzV0FvZE9Qb0J6QTE2MjY1ODQzOTMxNTc%3D",
        "time_in_seconds": 26.989,
    },
    {
        "author": {"id": "UCbcED252E4O3ImCavRrcOmA", "name": "Yamato Pendragon"},
        "message_type": "text_message",
        "message": "こん…",
        "message_id": "CjkKGkNPcVprb2ZyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDTHI3NzkzazZfRUNGWmVBWXdZZGlKc0lkZzA%3D",
        "time_in_seconds": 27.322,
    },
    {
        "author": {"id": "UCnofPFAHCQRx6RCSRMocnQQ", "name": "Unlimitedpensel Ch."},
        "message_type": "text_message",
        "message": "we are always family",
        "message_id": "CkUKGkNJbVZwWWZyNl9FQ0ZjVU5yUVlkQnlZQ3BREidDTWFreFlEcjZfRUNGUUw4andvZHBiNE1RUTE2MjY1ODQzOTEzODM%3D",
        "time_in_seconds": 27.636,
    },
    {
        "author": {"id": "UCTpD5MToIioDyGd_CG-_iBA", "name": "キリシェ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjoKGkNLandwSWZyNl9FQ0ZZRVhmUW9kWHY4SU53EhxDSkhiejRMcjZfRUNGY1NpNlFvZDNMZ0s5QS0w",
        "time_in_seconds": 27.644,
    },
    {
        "author": {"id": "UCS-1flTu56hfDpOd_vHy0PQ", "name": "Ruler"},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CkUKGkNKNjRxNGZyNl9FQ0ZjX0N3Z1FkUHl3RnRREidDTG5ZeGNIcTZfRUNGV3ZRY3dFZE10d01SdzE2MjY1ODQzNTg3OTI%3D",
        "time_in_seconds": 27.772,
    },
    {
        "author": {"id": "UCIng4BBVeYpFOs1ggKjFCpw", "name": "同志ジューコフ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNOYTJ0NGZyNl9FQ0ZjX0N3Z1FkUHl3RnRREhtDSkxobGF2bjZfRUNGVXRLaXdvZFpfY09iUTA%3D",
        "time_in_seconds": 27.895,
    },
    {
        "author": {"id": "UCJ_c9jsI3eWK5UYhHkCqZ8A", "name": "しみず"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNMUHh4SWZyNl9FQ0ZSUWRmUW9kU0dBQVFBEhtDUFBZcC1YcTZfRUNGUnBMWUFvZDRLUUI2UTA%3D",
        "time_in_seconds": 28.054,
    },
    {
        "author": {"id": "UCawGDcS4AlCizJkXM8DvFSg", "name": "まな板の上のぼんじり"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjoKGkNJZWYxNGZyNl9FQ0ZZRVhmUW9kWHY4SU53EhxDT0c5Z3ZQcTZfRUNGVU1aS2dvZG9Tb0l2dy0x",
        "time_in_seconds": 28.441,
    },
    {
        "author": {"id": "UCvL9iPvI7j_ph7eV37tltSw", "name": "renchan"},
        "message_type": "text_message",
        "message": "konyappi",
        "message_id": "CkUKGkNNbmJfNGZyNl9FQ0ZZVVo1d29keGl3SlBREidDSTZfcElYcjZfRUNGVVJDblFrZF8yOEVudzE2MjY1ODQzOTMwMzk%3D",
        "time_in_seconds": 29.171,
    },
    {
        "author": {"id": "UCw6g9yBkt54jUJI6elkdZzg", "name": "Khoa Nguyễn Văn"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNMYTFnNGpyNl9FQ0ZaTTFyUVlkRTVvRnRBEidDT19vaVlUcjZfRUNGWll4V0FvZFR1b0hQdzE2MjY1ODQzOTIzOTI%3D",
        "time_in_seconds": 29.199,
    },
    {
        "author": {"id": "UC1VH0O1b9QgCOIH1X7xseyA", "name": "Davide Ciappeddu"},
        "message_type": "text_message",
        "message": "こん:_やっぴー:!!",
        "message_id": "CjkKGkNLVG1oNGpyNl9FQ0ZZbUt3UW9ka1NNRXpREhtDSmFoaklmZzZfRUNGZGhGZWdVZERvOE9EUTE%3D",
        "time_in_seconds": 29.343,
    },
    {
        "author": {"id": "UCP0xmqQQz_3zTLFjlnaltnQ", "name": "Eternal DIVE PART II"},
        "message_type": "text_message",
        "message": "KON:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNJVEprb2pyNl9FQ0ZaRU5yUVlkQ0I4UEpnEhtDTDJYOE1ITTZfRUNGVXpBb0FJZHlsQUNfUTA%3D",
        "time_in_seconds": 29.358,
    },
    {
        "author": {"id": "UCkeXQfnuNYw8L0XEt2jFYow", "name": "夕焼け"},
        "message_type": "text_message",
        "message": "こんやっぴー",
        "message_id": "CjoKGkNMZmRvWWpyNl9FQ0ZkZ0FyUVlkdVBRRlFREhxDSi1NaDRYcjZfRUNGVGZIVEFJZDFUY0hhZy0w",
        "time_in_seconds": 29.612,
    },
    {
        "author": {"id": "UCLCzX3g8v7L31mdtUj-RpiA", "name": "大チャン丸"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNMN0pySWpyNl9FQ0ZkTVE1d29kZFdVTnBREidDUHpFb1lYcjZfRUNGY05BS2dvZFNYUUp2dzE2MjY1ODQzOTMzMjc%3D",
        "time_in_seconds": 29.793,
    },
    {
        "author": {"id": "UCaNDV8TEahSX5thUaomnkeQ", "name": "CireLink"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNOWExwb2pyNl9FQ0ZiVE93UW9kbzlZTzF3EhtDUHVrdklYZDZfRUNGWXdFaVFvZC1SQUI3dzA%3D",
        "time_in_seconds": 29.809,
    },
    {
        "author": {"id": "UCfdspicLNAaO62ZiAnSJaVg", "name": "Spherical Cow in Vacuum"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNLal9xSWpyNl9FQ0ZjakZ3UW9kbkVJUFBREhtDTkNJZ1liZzZfRUNGY1Jsc2dvZFY2Y1A0dzE%3D",
        "time_in_seconds": 29.819,
    },
    {
        "author": {"id": "UCrQxhRKwzS7VQ205o2swdww", "name": "Iruka Syake Σ"},
        "message_type": "text_message",
        "message": "楽しみやー",
        "message_id": "CjoKGkNPbnBzb2pyNl9FQ0ZZVVo1d29keGl3SlBREhxDTlBDMjRMcjZfRUNGU2NOclFZZHZhWUQ3QS0w",
        "time_in_seconds": 29.932,
    },
    {
        "author": {"id": "UCzZBdhci4gqqOkyjsGclqCg", "name": "シャイニング💠ゼタ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNKYjF2b2pyNl9FQ0ZaTTFyUVlkRTVvRnRBEidDSnVjb29QcjZfRUNGYm9DdHdBZGxKZ0pMQTE2MjY1ODQzOTM1OTc%3D",
        "time_in_seconds": 30.131,
    },
    {
        "author": {"id": "UCBzODiX5d9H0hI_qbe4ywQA", "name": "wareルラ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNNNzN1NGpyNl9FQ0ZVUFh3UW9kc1pzRC13EhtDTHplcklQcjZfRUNGVVJsbUFvZEVMSUQ0dzA%3D",
        "time_in_seconds": 30.142,
    },
    {
        "author": {"id": "UCnDdoNtN-HW4XzmRvTX-axQ", "name": "Dark Rose"},
        "message_type": "text_message",
        "message": "Konyappi!:_トワ様いえーい:",
        "message_id": "CkUKGkNPN3M2NGpyNl9FQ0ZVUFh3UW9kc1pzRC13EidDS0tpcW9YcjZfRUNGVTBGMWdBZHcyQUYydzE2MjY1ODQzOTUxNTE%3D",
        "time_in_seconds": 30.63,
    },
    {
        "author": {"id": "UCTdoDKnYYBvoOWYozk7CRow", "name": "Zain"},
        "message_type": "text_message",
        "message": "こんやっぴー",
        "message_id": "CjkKGkNJV2QtNGpyNl9FQ0ZjX0N3Z1FkUHl3RnRREhtDTm0yMl9UbTZfRUNGWmJBb0FJZElwTUtjZzE%3D",
        "time_in_seconds": 31.175,
    },
    {
        "author": {"id": "UCTWtqmbyTK_JZ7_vUOGTlZQ", "name": "Lost Lenore"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNMN2lwWW5yNl9FQ0ZkTVE1d29kZFdVTnBREhtDTnZhc2VmcTZfRUNGY2dydHdBZEFkQUNRUTA%3D",
        "time_in_seconds": 31.862,
    },
    {
        "author": {"id": "UCDtd_p0SMZg__9oDL0XKxLg", "name": "白神山桜桃"},
        "message_type": "text_message",
        "message": "こんにちは",
        "message_id": "CjkKGkNOVzlyb25yNl9FQ0ZZRVhmUW9kWHY4SU53EhtDT2YzanQ3UjZfRUNGVVdPandvZGNVZ0R2dzA%3D",
        "time_in_seconds": 32.035,
    },
    {
        "author": {"id": "UCCcJWBqb36oV2y8puusQuFg", "name": "#くろまゆ"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様キラキラ:",
        "message_id": "CkUKGkNOckh1b25yNl9FQ0ZkZ0FyUVlkdVBRRlFREidDSkNXbUlmcjZfRUNGUnFfV0FvZGRFa0czZzE2MjY1ODQzOTYwNzY%3D",
        "time_in_seconds": 32.161,
    },
    {
        "author": {"id": "UCETr-d9EXiTNAWFyLtuf4-A", "name": "V Smash"},
        "message_type": "text_message",
        "message": "Towa ",
        "message_id": "CjkKGkNKM3J5NG5yNl9FQ0ZVd01zd0FkQ2hZRFpBEhtDTkt1aGZfcTZfRUNGZUU1c3dBZFg2QUQ0dzA%3D",
        "time_in_seconds": 32.498,
    },
    {
        "author": {"id": "UCuElP0-rAl3tUQw-Tvr1ZXA", "name": "烏龍"},
        "message_type": "text_message",
        "message": "こん:_やっぴー:",
        "message_id": "CjkKGkNQS1AwNG5yNl9FQ0ZjTWZmUW9kWlJzSXFBEhtDTFNWd2NibzZfRUNGZmktWXdZZHIzQUVzdzE%3D",
        "time_in_seconds": 32.585,
    },
    {
        "author": {"id": "UCA_ASTgW7mJy7u79oh3GjWQ", "name": "Angel G"},
        "message_type": "text_message",
        "message": "LETS GOOOOOO",
        "message_id": "CjoKGkNKbnA1NG5yNl9FQ0ZSUWRmUW9kU0dBQVFBEhxDTFNEdnFycTZfRUNGWkNyeEFvZHdpUUp2dy0z",
        "time_in_seconds": 32.881,
    },
    {
        "author": {"id": "UCaMEzwyR-ZRSB6_8Pn4dPow", "name": "themoobz"},
        "message_type": "text_message",
        "message": "kon :_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNPV3M3WW5yNl9FQ0ZlQU5yUVlkMTJrS1FBEhtDT3JOMk1UcTZfRUNGV241T0FZZGtBQU8tUTA%3D",
        "time_in_seconds": 33.018,
    },
    {
        "author": {"id": "UCm7LKZTa5yps-Bdq9wt5JTA", "name": "Athreides"},
        "message_type": "text_message",
        "message": "Towa-sama Te Amo",
        "message_id": "CkUKGkNKWGstSW5yNl9FQ0ZZVU9aUW9kSno0TmZ3EidDTHEzcVlUcjZfRUNGWlFTc3dBZG9fNEJBUTE2MjY1ODQ0MDA4MTU%3D",
        "time_in_seconds": 33.266,
    },
    {
        "author": {"id": "UC4jDvtngZKECpncKxp-NkmQ", "name": "vivianpigeon"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjoKGkNJUzVfWW5yNl9FQ0ZkZ0FyUVlkdVBRRlFREhxDTGpzajRicjZfRUNGYzB3S2dvZDFVY0JVQS0w",
        "time_in_seconds": 33.318,
    },
    {
        "author": {"id": "UCBJSteJ5LvA8mxoRj0hb_QQ", "name": "avie"},
        "message_type": "text_message",
        "message": ":_トワ様いえーい::_トワ様いえーい:",
        "message_id": "CkUKGkNQX3VuWXJyNl9FQ0ZWb1ByUVlkVFg4RHVBEidDS0xmNjREcjZfRUNGYWZhY3dFZHhpc0daUTE2MjY1ODQzOTc1NDQ%3D",
        "time_in_seconds": 33.83,
    },
    {
        "author": {"id": "UC6kXeTikSiGiZrTzQEfZZfg", "name": "ラベル"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNOZjd6SXJyNl9FQ0ZaTTFyUVlkRTVvRnRBEidDT3VENDREcjZfRUNGZGR0V0FvZHNxQUQ0UTE2MjY1ODQzOTg1MDA%3D",
        "time_in_seconds": 34.635,
    },
    {
        "author": {"id": "UCLeLH-PQA2ADFOW1AorGUZw", "name": "Hannah Althea"},
        "message_type": "text_message",
        "message": "Konyappi!",
        "message_id": "CjkKGkNLSEU0SXJyNl9FQ0ZWb1ByUVlkVFg4RHVBEhtDTWI3OF96cTZfRUNGVU5IaFFvZFRBVUdydzE%3D",
        "time_in_seconds": 34.956,
    },
    {
        "author": {"id": "UCTSkltVDCgsx_Ct4nG7BFOQ", "name": "UBIKユービック"},
        "message_type": "text_message",
        "message": "こんやっぴー",
        "message_id": "CjkKGkNMQ0M2b3JyNl9FQ0ZaRU5yUVlkQ0I4UEpnEhtDSzdKdFBybTZfRUNGVkpPandvZDdRVUtQdzA%3D",
        "time_in_seconds": 35.054,
    },
    {
        "author": {"id": "UClCtIGFA3V_Tl8jZ8Qd7ZQg", "name": "Dif. Nurina"},
        "message_type": "text_message",
        "message": "kon...:_トワ様いえーい::_トワ様いえーい:",
        "message_id": "CjkKGkNMU2Nfb3JyNl9FQ0ZWb1ByUVlkVFg4RHVBEhtDS3JBNWRyazZfRUNGUTdLY3dFZDY3VU45dzA%3D",
        "time_in_seconds": 35.309,
    },
    {
        "author": {"id": "UCaOs981VIHeNUg6l27mza_w", "name": "Chatsubo"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjkKGkNPUHdqWXZyNl9FQ0ZkZ0FyUVlkdVBRRlFREhtDSUgzeTY3VDZfRUNGY0VsV0FvZEt6NFA0UTE%3D",
        "time_in_seconds": 35.606,
    },
    {
        "author": {"id": "UCtSNv6VgO9Wx7YN8yqlbnMg", "name": "miha 398"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CjoKGkNKemtuSXZyNl9FQ0ZkTVE1d29kZFdVTnBREhxDSmItNGVYcTZfRUNGUUx4T0FZZEhINE1CQS0z",
        "time_in_seconds": 35.913,
    },
    {
        "author": {"id": "UCFJ4GmJv2ZR3jk9bE8yZ8Zg", "name": "はしよし"},
        "message_type": "text_message",
        "message": "こん:_やっぴー:",
        "message_id": "CjoKGkNJZm50WXZyNl9FQ0ZSd2RyUVlkb25FQnR3EhxDT3pEdlBucTZfRUNGZmRDblFrZDlPSUZwdy0w",
        "time_in_seconds": 36.302,
    },
    {
        "author": {"id": "UCH7XtmT0tC-C9RWitB3iemQ", "name": "呵呵"},
        "message_type": "text_message",
        "message": "hi hi",
        "message_id": "CkUKGkNMbkwwSXZyNl9FQ0ZkZ0FyUVlkdVBRRlFREidDTzNFaFlIcjZfRUNGY1IxWUFvZDh0SUpfZzE2MjY1ODQ0MDEwMDU%3D",
        "time_in_seconds": 37.058,
    },
    {
        "author": {"id": "UCE_wvQWLW4ObwEt0-xDBdwg", "name": "Revi"},
        "message_type": "text_message",
        "message": "konyappi",
        "message_id": "CkUKGkNMLTg2WXZyNl9FQ0ZkZ0FyUVlkdVBRRlFREidDTWVVNjRicjZfRUNGVkZBOVFVZDhXa0IzdzE2MjY1ODQ0MDA3MjA%3D",
        "time_in_seconds": 37.134,
    },
    {
        "author": {"id": "UC7Cx27KiMdKtoFIEpC6mRsA", "name": "In9lp"},
        "message_type": "text_message",
        "message": ":_トワ様いえーい:",
        "message_id": "CkUKGkNNcl85b3ZyNl9FQ0ZSYml3UW9kUDAwRy13EidDTmJxdG9mcjZfRUNGYWVrVVFvZEVvMEdIQTE2MjY1ODQ0MDIzMDI%3D",
        "time_in_seconds": 37.502,
    },
    {
        "author": {"id": "UCNDoIL08saEOTZqshRDbOwQ", "name": "ゆきにゃん"},
        "message_type": "text_message",
        "message": "こんやっぴ〜",
        "message_id": "CjoKGkNNT2tqSXpyNl9FQ0ZkZ0FyUVlkdVBRRlFREhxDT3pNLV9fcTZfRUNGYWRDaFFvZFBqd01Xdy0x",
        "time_in_seconds": 37.76,
    },
    {
        "author": {"id": "UChqeFbRtb6abcTRYIY9NBmg", "name": "Mario Olvera"},
        "message_type": "text_message",
        "message": "Let's go my Towa-sama",
        "message_id": "CkUKGkNQVFNsSXpyNl9FQ0ZZVVo1d29keGl3SlBREidDUE8yX0licjZfRUNGYjZuNVFjZGFPY0lhZzE2MjY1ODQzOTcyOTQ%3D",
        "time_in_seconds": 37.941,
    },
    {
        "author": {"id": "UCa2LRcxVk0sQRvMei5ssc3g", "name": "佑偉"},
        "message_type": "text_message",
        "message": "こん:_やっぴー::_トワ様いえーい:",
        "message_id": "CkUKGkNJTGpzSXpyNl9FQ0ZkZ0FyUVlkdVBRRlFREidDT3JXMDRIcjZfRUNGZkZBOVFVZHNBME55ZzE2MjY1ODQ0MDQwNzM%3D",
        "time_in_seconds": 38.242,
    },
    {
        "author": {"id": "UCmkvlGCNxsOKYfziLdC4elw", "name": "SerackSK"},
        "message_type": "text_message",
        "message": "Kon…",
        "message_id": "CjkKGkNOTGdyWXpyNl9FQ0ZRcGI3UW9kLTJRRkNREhtDTVBadE12cTZfRUNGVDdCRmdrZHJnRUJZUTA%3D",
        "time_in_seconds": 38.381,
    },
    {
        "author": {"id": "UC0CE_L15OAYiOwRgm7cUA-A", "name": "TMT"},
        "message_type": "text_message",
        "message": "YOSHA",
        "message_id": "CjoKGkNQTFcwWXpyNl9FQ0ZSd2RyUVlkb25FQnR3EhxDT09MM29UcjZfRUNGUjB6dHdBZHhPUUdhdy0w",
        "time_in_seconds": 38.849,
    },
    {
        "author": {"id": "UC7HlfysV2CqxKvjd6d5NxCw", "name": "Haru [春]"},
        "message_type": "text_message",
        "message": "こん...",
        "message_id": "CkUKGkNJS0wyWXpyNl9FQ0ZZRVhmUW9kWHY4SU53EidDTzZveUlmcjZfRUNGVGZaVEFJZHlEQUxYdzE2MjY1ODQ0MDIxODM%3D",
        "time_in_seconds": 38.978,
    },
    {
        "author": {"id": "UCuPkyqDfoIHYl-sSfhdDtDw", "name": "Yuzuchu"},
        "message_type": "text_message",
        "message": "こんやっぴ~",
        "message_id": "CkUKGkNQYU01b3pyNl9FQ0ZSd2RyUVlkb25FQnR3EidDT3ZQc29mcjZfRUNGUmlteEFvZDdPQU9ZdzE2MjY1ODQ0MDQ0NjU%3D",
        "time_in_seconds": 39.347,
    },
    {
        "author": {"id": "UCidkF_9XheO7n4Bq8FsSwbw", "name": "Hios_Ai"},
        "message_type": "text_message",
        "message": "konyappi~~~",
        "message_id": "CkUKGkNJUzg2b3pyNl9FQ0ZaTTFyUVlkRTVvRnRBEidDT2Y0NW9icjZfRUNGUXc3V0FvZEpMd0JYdzE2MjY1ODQ0MDMzNzk%3D",
        "time_in_seconds": 39.352,
    },
]

if __name__ == "__main__":
    unittest.main()
