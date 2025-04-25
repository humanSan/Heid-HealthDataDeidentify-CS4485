import re

# takes original and deidentified string and returns the difference
# in the form of a list of tuples (deidenfified phi, original phi)
def get_differences(original: str, deid: str):
    spans = [(match.start(), match.end()) for match in re.finditer(r'\*[^*]+\*', deid)]
    phis = [deid[start:end] for start, end in spans]

    # Replace phis in deid with placeholder
    placeholder = '\uFFFF'
    clean_deid = re.sub(r'\*[^*]+\*', placeholder, deid)

    differences = []

    #pointers in clean_deid and original
    i = 0
    j = 0
    while i < len(clean_deid) and j < len(original):
        # found replacement
        if clean_deid[i] == placeholder:
            nextchar = clean_deid[i+1]
            replacement_start = j
            replacement_end = j
            # try to find correct realignment point
            while True:
                replacement_end += 1
                if replacement_end >= len(original):
                    break
                if original[replacement_end] == nextchar:
                    check_pointer_mod = i + 2
                    check_pointer_orig = replacement_end + 1
                    while check_pointer_mod < len(clean_deid) and check_pointer_orig < len(original) and clean_deid[check_pointer_mod] == original[check_pointer_orig]:
                        check_pointer_mod += 1
                        check_pointer_orig += 1
                    if check_pointer_mod >= len(clean_deid) or clean_deid[check_pointer_mod] == placeholder:
                        # found realignment point, add replaced string to differences
                        differences.append(original[replacement_start-1:replacement_end])
                        break
            j = replacement_end
        i += 1
        j += 1
    
    return list(zip(phis, differences))


# TODO
def get_hashed_differences(original, deid):
    pass