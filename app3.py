import re

# Replaces matches of a pattern with unique identifiers iteratively, keeping category names and counts.
def replace_with_unique_identifier_iterative_selective(text, pattern, prefix, replaced_count=None, running_id_map=None):
    if running_id_map is None:
        running_id_map = {}
    if replaced_count is None:
        replaced_count = {}
    count = replaced_count.get(prefix, 0)

    def replace(match):
        nonlocal count
        count += 1
        replaced_count[prefix] = count
        identifier = f"{prefix}#{count}"

        # The sensitive information is in the second capturing group
        running_id_map[identifier] = match.group(2)
        # The header is in the first capturing group
        return f"{match.group(1)}{' ' if match.group(1) else ''}[{identifier}]"

    return re.sub(pattern, replace, text), replaced_count

with open("matchers/honorifics.txt", "r") as file:
    re_matcher = ""
    for line in file:
        re_matcher = re_matcher + "|" + line.strip()
    # remove the leading pipe |
    re_matcher = "(?:" + re_matcher[1:] + ")"

# De-identifies EHR text by iteratively replacing only the sensitive information to keep track of what was replaced.
def deidentify_ehr_iterative_selective(text):
    replaced_counts = {}
    de_id_map = {}
    updated_text = text

    patterns = [
        (r"(Patient name:|Provider name:|Patient:|Provider:|Patient Name:|Provider Name:)\s*((?:" + re_matcher + r"\.\s*)?[A-Z][a-z]+(?:[ ][A-Z][a-z]+)*)", "NAME"),
        (r"()(" + re_matcher + r"\.\s*[A-Z][a-z]+(?:[ ][A-Z][a-z]+)*)", "NAME"),
        (r"(Address:)\s*((?:[^,\n]+?)(?:,\s*Apt\s*(?:[^\n,]+?))?(?:,\s*)(?:[^,\n]+?,\s*)?(?:[A-Z]{2})\s*(?:\d{5}(?:-\d{4})?))", "ADDRESS"),
        (r"(Date of Birth:|DoB:|DOB:)\s*(\d{2}/\d{2}/\d{4})", "DOB"),
        (r"(SSN:)\s*([0-9*]{3}-[0-9*]{2}-[0-9*]{4})", "SSN"), # Capture the word boundary and SSN
        (r"(Phone:)\s*(\d{3}-\d{3}-\d{4})", "PHONE"),
        (r"(email:|Email:)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "EMAIL"),
        (r"(Medicaid account:|Account:)\s*(\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b)", "ACCOUNT"),
        (r"(Hospital name:|Hospital Name:)\s*(\w+(?: \w+)+)", "HOSPITAL"),
        (r"(Lab Results(?:\s*\((?:\d{2}/\d{2}/\d{4})\))?:)((?:\n-\s.+)+)", "LAB"),
        (r"(Allergies:)((?:\n-?\s(?![\w ]+:).+)+)", "ALLERGIES"),
        (r"(Health plan beneficiary number:)\s*(\d{3}-\d{4}-\d{4})", "NUMBER"),
        (r"(Device identifier:)\s*([A-Za-z0-9]{6}-[A-Za-z0-9]{8})", "NUMBER"),
        (r"(Pacemaker serial numbers:)\s*([A-Za-z0-9]{5}-[A-Za-z0-9]{7})", "NUMBER"),
        (r"(Medical record number:)\s*([A-Za-z0-9]{7}-[A-Za-z0-9]{7})", "NUMBER"),
        (r"(license number:)\s*([A-Za-z0-9]{4}-[A-Za-z0-9]{6})", "NUMBER"),
        (r"(Certificate number:)\s*([A-Za-z0-9]{6}-[A-Za-z0-9]{4})", "NUMBER"),
        (r"(Health Insurance:)\s*([A-Za-z0-9]{5}-[A-Za-z0-9]{10})", "NUMBER"),
        (r"(Group no\.:)\s*(\d{6})", "NUMBER"),
        (r"(Fax number:|Fax no\.:)\s*(\d{3}-\d{3}-\d{4})", "NUMBER"),
        (r"(URL:)\s*((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\))+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", "URL"),
        (r"(Code:)\s*(\d+)", "NUMBER"),
    ]

    previous_text = None
    while previous_text != updated_text:
        previous_text = updated_text
        for pattern, prefix in patterns:
            updated_text, replaced_counts = replace_with_unique_identifier_iterative_selective(
                updated_text, pattern, prefix, replaced_counts, de_id_map
            )

    return updated_text, de_id_map


with(open("ehr EC 3 .txt") as phi2):
    ehr_text = ''.join(list(phi2.readlines()))

    # Apply the selective iterative de-identification function
    deidentified_ehr, id_map = deidentify_ehr_iterative_selective(ehr_text)
    print(deidentified_ehr, id_map)