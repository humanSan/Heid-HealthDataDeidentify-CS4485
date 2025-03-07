import re


def strip_emails(text: str, two_way=False, sub="*email*"):
    # substitute emails using regex
    return re.sub(r"[\w.%+-]+@[\w.]+\.[A-Za-z]+", sub, text)