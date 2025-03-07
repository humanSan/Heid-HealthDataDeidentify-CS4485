import re

# honorifics.txt reference: https://gist.github.com/neilhawkins/c7bb94e5b7ae558e826989d330418938#file-list-of-salutations-titles-honorifics-txt
with open("./matchers/honorifics.txt", "r") as file:
    re_matcher = ""
    for line in file:
        re_matcher = re_matcher + "|" + line.strip()
    # remove the leading pipe |
    re_matcher = "(?:" + re_matcher[1:] + ")"

# TODO: support bidirectionality
# we assume that all names start with a capital letter
def strip_names(text: str, two_way=False, sub="*name*"):
    new_text = text

    # compile the honorific matcher, this assumes names are the format of <honorific>.? <Name> <Name> ...
    honorific_matcher = re.compile(re_matcher + r"\.?(?:(?! \w+:)( [A-Z]\w+)){1,3}")
    names = honorific_matcher.findall(new_text)
    new_text = re.sub(honorific_matcher, sub, new_text)

    # we take any last names we find and try to remove regular names from those
    for name in names:
        name_matcher = re.compile(r"(?!:)([A-Z]\w+ )+" + name.strip() + r"(?:(?! \w+:)( [A-Z]\w+))?")
        new_text = re.sub(name_matcher, sub, new_text)

    # if there aren't any matched names, do a dumb lookup for headers and remove based on that
    if len(names) == 0:
        matcher = re.compile(r"^(?P<label>Patient|Provider): .*$", flags=re.MULTILINE)
        new_text = re.sub(matcher, lambda match: match.group('label') + ": " + sub, new_text)

    return new_text

def restore_names():
    pass