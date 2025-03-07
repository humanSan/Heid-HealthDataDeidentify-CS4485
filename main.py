import re

with open("ehr JMS.txt", "r") as file:
    txt = file.read()

    # substitute dates using regex
    # covers dates in the form 03/07/2025, 3-7-25, etc.
    txt = re.sub(r"\d{1,2}([\/-])\d{1,2}\1\d{2,4}", "*date*", txt)

    # substitute emails using regex
    txt = re.sub(r"[\w.%+-]+@[\w.]+\.[A-Za-z]+", "*email*", txt)

    # substitute phone numbers using regex
    # works only for 10-digit numbers with optional +1
    txt = re.sub(r"(\+1\s*)?\(?(\d{3})\)?\s*-?\d{3}-?\s*\d{4}", "*phonenum*", txt)

    print(txt)