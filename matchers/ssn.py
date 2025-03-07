import re


def strip_ssn(text: str, two_way=False, sub="*ssn*"):
    return re.sub(r"\d{3}[-]\d{2}[-]\d{4}", sub, text)