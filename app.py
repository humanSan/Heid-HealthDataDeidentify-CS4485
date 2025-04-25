import os
from io import StringIO
import streamlit as st
from dotenv import load_dotenv
import re
from matchers.addresses import strip_addresses
from matchers.dates import *
from matchers.emails import strip_emails
from matchers.names import strip_names
from matchers.phonenums import strip_phone_nums
from matchers.ssn import strip_ssn
from reidentification import *
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types
import yaml
import ast

load_dotenv()
client = genai.Client()

st.set_page_config(
        page_title="DeIdentify Health Info",
)



phi_list = ["Doc Name", "Patient Name", "All Names", "Social Worker Names", "Date of Birth", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medicaid Account", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code", "Provider Name", "Hospital Name", "Allergies", "Lab Results"]

phi_dict = {}

phi_dict["PHI 3"] = ["All Names", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code"]

phi_dict["PHI 2"] = ["Patient Name", "Doc Name", "Date of Birth", "SSN", "Address", "Email", "Provider Name", "Hospital Name", "Allergies", "Lab Results", "Medicaid Account", "Social Worker Names", "Phone Number"]

with open("prompts.yaml", "r") as prompt_file:
   phi_prompts = yaml.safe_load(prompt_file)

print(phi_prompts)

phi = None




# Session States
# 0. Homepage, upload file for deidentification
# 1. File uploaded, show user their file
# 2. File deidentified, show user deidentified file
# 3. Upload files for reidentification
# 4. File reidentified

if 'state' not in st.session_state:
   st.session_state.state = 0

if 'input' not in st.session_state:
   st.session_state.input = ""

if 'output' not in st.session_state:
   st.session_state.output = ""

if 'reid_map' not in st.session_state:
   st.session_state.reid_map = None

if 'file' not in st.session_state:
   st.session_state.file = None

st.header("Health Data Deidentifier")

if st.session_state.state <= 2:
   if st.sidebar.button("Reidentify Record", type="primary"):
      st.session_state.state = 3
      st.session_state.input = ""
      st.session_state.output = ""
      st.session_state.reid_map = None
      st.session_state.file = None
      st.rerun()
   method = st.sidebar.radio("Method", ["LLM", "RegEx"])
   if method == "RegEx":
      phi_no = st.sidebar.radio("PHI List", ["PHI 1", "PHI 3"])
   elif method == "LLM":
      phi_no = st.sidebar.radio("PHI List", ["PHI 2", "PHI 3"])
      phi = st.sidebar.multiselect("PHI Items", phi_list, default=phi_dict[phi_no])
else:
   if st.sidebar.button("Deidentify Record", type="primary"):
      st.session_state.state = 0
      st.session_state.input = ""
      st.session_state.output = ""
      st.session_state.reid_map = None
      st.session_state.file = None
      st.rerun()

def reidentify(ehr_text, reid_map):
   # return "Ha nothing here"
   #text is a string, reid is a dictionary
   text = ehr_text
   print(type(reid_map))
   for item in reid_map:
      print(item)
      lookfor = "["+item+"]"
      text = text.replace(lookfor, reid_map[item])
   
   return text

def deidentify():
   phiList = []
   with(open("phi2.txt") as phi2):
      phiList = phi2.readlines()
   
   # substitute dates using regex
   # covers dates in the form 03/07/2025, 3-7-25, etc.
   if len(st.session_state.input) > 0:
      txt = st.session_state.input

      print(type(txt))
      

      if(method=="RegEx"):
         if(phi_no=="PHI 1"):
            # substitute emails using regex

            print(txt)
            txt = strip_emails(txt)
            txt = strip_phone_nums(txt)
            txt = strip_names(txt)
            txt = strip_addresses(txt)

            lines = txt.splitlines()

            DOBs = ["dob", "d.o.b.", "date of birth", "dateof birth", "date ofbirth", "dateofbirth", "date-of-birth", "birthday", "birth day", "birth-day"]

            for i in range(0, len(lines)):
               lowered = lines[i].lower()
               if "ssn" in lowered or "social security" in lowered or "s.s.n." in lowered:
                  lines[i] = strip_ssn(lines[i])
               
               for dob in DOBs:
                  if dob in lowered:
                     lines[i] = strip_dob(lines[i])
                     break

            st.session_state.output = "\n".join(lines)

         elif(phi_no=="PHI 3"):

            deidentified_ehr, id_map = deidentify_ehr_iterative_selective(txt)
            print(deidentified_ehr, id_map)

            st.session_state.output = deidentified_ehr
            st.session_state.reid_map = str(id_map)


      elif(method=="LLM"):
         prompt = ""
         
         remove_items = [phi_prompts[item] for item in phi]

         
         prompt = """
                  Task: Please anonymize the following clinical note using these instructions:

                  """ + "\n".join(remove_items) + """

                  An example: The string "Dr. Alex can be called at 654-123-7777" should become "*name* can be called at *phone*"

                  You should only replace personal information and not generic words. For example, if the word 'Name' or 'Phone' appears in the health record, it should NOT be replaced with '*name*' or '*phone*'. ONLY replace words that contain actual personal information
                  
                  If the word for the information itself is in the record, like the word "Phone", do not replace it with *phone*. Only the actual personal information should be replaced.
                  THE OUTPUT SHOULD INCLUDE ONLY THE ANONYMIZED HEALTH RECORD WITH NO OTHER TEXT.

                  Health Record:

                  """ + txt
         
         #print(prompt)

         response = client.models.generate_content(
            model = "gemini-1.5-flash",
            config=types.GenerateContentConfig(
               temperature=0
            ),
            contents=[prompt]
         )
         #print(response)
         st.session_state.output = response.text


      st.session_state.state = 2

if st.session_state.state < 2:
   if st.session_state.file == None:
      st.session_state.file = st.file_uploader(label = "Upload file here.", type=['txt', 'md'])
      
   if st.session_state.file is not None:
      if(st.session_state.state==0):
         st.session_state.state = 1
         st.rerun()

      data = st.session_state.file.getvalue()
      stringio = StringIO(data.decode())
      st.session_state.input = stringio.read()
      st.write("")
      st.markdown(f"### Your Input Record - {st.session_state.file.name}")
      st.text(st.session_state.input)
      st.write("")
      state = st.button("Deidentify Record", on_click = deidentify)
elif st.session_state.state == 2:

   # PLEASE PUT CODE FOR REIDENTIFICATION HERE

   # to get the ORIGINAL phi, use st.session_state.input
   # to get the DEIDENTIFIED phi, use st.session_state.output
   # if you want any data to persist across streamlit page refreshes, you MUST use st.session_state.var, not just var = data

   # FIRST: we need to figure out which items were actually removed. to do this, iterate over the lines in the deidentified phi, and for every tag like *name*, *date*, etc, look at the same line in the original phi, and find out which characters were removed
   # Put these deidentified items in a dictionary, or write them to a file
   # Take those items and hash them or whatever you need to do for reidentification

   st.markdown("""### Record Deidentified!""")
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-deidentified.txt"
   st.download_button(label="Download Deidentified Record", data=st.session_state.output, file_name=download_name, mime="text/plain")

   reid_download_name = os.path.splitext(st.session_state.file.name)[0] + "-reid_map.txt"
   if(st.session_state.reid_map is not None):
      st.download_button(label="Download Reidentification Map", data=st.session_state.reid_map, file_name=reid_download_name, mime="text/plain")
   st.text(st.session_state.output)
   
elif st.session_state.state == 3:
   st.subheader("Reidentification Mode")
   st.session_state.file = st.file_uploader(label = "Upload DEIDENTIFIED record here.", type=['txt', 'md'])

   st.session_state.reid_map = st.file_uploader(label = "Upload REIDENTIFICATION map here.", type=['txt', 'md'])
   
   if st.session_state.file is not None and st.session_state.reid_map is not None:
      if st.button("Reidentify Record"):

         data = st.session_state.file.getvalue()
         stringio = StringIO(data.decode())
         st.session_state.input = stringio.read()

         reid_data = st.session_state.reid_map.getvalue()
         stringio = StringIO(reid_data.decode())
         st.session_state.reid_map = ast.literal_eval(stringio.read())
         
         
         #data is a string, reid_data is a python dictionary
         st.session_state.output = reidentify(st.session_state.input, st.session_state.reid_map)

         st.session_state.state = 4
         st.rerun()
elif st.session_state.state == 4:
   st.markdown("""### Record Reidentified!""")
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-reidentified.txt"
   st.download_button(label="Download Reidentified Record", data=st.session_state.output, file_name=download_name, mime="text/plain")
   #st.text(st.session_state.input)
   #st.text(str(st.session_state.reid_map))
   st.text(st.session_state.output)


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
        (r"(Date of Birth:|DoB:|DOB:)\s*(\d{2}/\d{2}/\d{4})", "DATE"),
        (r"()\s*(\d{2}/\d{2}/\d{4})", "DATE"),
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


with(open("ehr EC 3.txt") as phi2):
    ehr_text = ''.join(list(phi2.readlines()))

    # Apply the selective iterative de-identification function
    deidentified_ehr, id_map = deidentify_ehr_iterative_selective(ehr_text)
   #  print(deidentified_ehr, id_map)