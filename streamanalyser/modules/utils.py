percentage = lambda current, out_of: round(int(current * 100 / out_of))


def normalize(text) -> str:
    """Normalizes string by removing punctuations, trimming and lowering.
    If a string only consists of punctuations, the text is trimmed only."""

    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""  # maybe add ？！ー～…
    if all(ch in punctuation for ch in text):
        return text.strip()
    return text.lower().strip().translate(str.maketrans("", "", punctuation))
