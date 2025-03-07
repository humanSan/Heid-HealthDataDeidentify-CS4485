import re

with open("ehr JMS.txt", "r") as file:
    txt = file.read()

    # substitute dates with regex
    # covers dates in the form 03/07/2025, 3-7-25, etc.
    txt = re.sub(r"\d{1,2}([\/-])\d{1,2}\1\d{2,4}", "*date*", txt)

    print(txt)