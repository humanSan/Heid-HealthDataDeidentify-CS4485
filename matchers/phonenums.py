import re


def strip_phone_nums(text: str, two_way=False, sub="*phone*"):
    # substitute phone numbers using regex
    # works only for 10-digit numbers with optional +1
    return re.sub(r"(\+1\s*)?\(?(\d{3})\)?\s*-?\d{3}-?\s*\d{4}", sub, text)