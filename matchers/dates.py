import re


def strip_dates(text: str, two_way=False, sub="*date*"):
    # covers dates in the form 03/07/2025, 3-7-25, etc.
    return re.sub(r"\d{1,2}([\/-])\d{1,2}\1\d{2,4}", sub, text)

def strip_dob(text: str, two_way=False, sub="*dob*"):
    # covers dates in the form 03/07/2025, 3-7-25, etc.
    return re.sub(r"\d{1,2}([\/-])\d{1,2}\1\d{2,4}", sub, text)