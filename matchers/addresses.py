import re


def strip_addresses(text: str, two_way=False, sub="*address*"):
    return re.sub(
        r"\b(\d{1,5}(\s\w+)+),([ -]([A-Z][a-z]+|\d+[A-Za-z]))+([, -]+([A-Z][a-z]+|[A-Z]{2,3}))*([, -]+(\d{4,6}))+([, -]+([A-Z][a-z]+|[A-Z]{2,3}))*",
        sub, text)