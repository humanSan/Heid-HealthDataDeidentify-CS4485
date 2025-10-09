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
import copy
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets
import uuid
from crypt import *

load_dotenv()
client = genai.Client()

st.set_page_config(
        page_title="Heid: Deidentify Health Data",
)



phi_list = ["Doc Name", "Patient Name", "All Names", "Social Worker Names", "Date of Birth", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medicaid Account", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code", "Provider Name", "Hospital Name", "Allergies", "Lab Results", "Medication"]

phi_dict = {}

phi_dict["All PHI"] = phi_list

phi_dict["PHI List 3"] = ["All Names", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code"]

phi_dict["PHI List 2"] = ["Patient Name", "Doc Name", "Date of Birth", "SSN", "Address", "Email", "Provider Name", "Hospital Name", "Allergies", "Lab Results", "Medicaid Account", "Social Worker Names", "Phone Number"]

phi_dict["PHI List 1"] = ["All Names", "Address", "Date of Birth", "SSN", "Phone Number", "Email"]

regex_match_dict = {
        "Name" : "NAME_MATCHERS",
        "Address" : "ADDRESS_MATCHERS",
        "Date of Birth": "DOB_MATCHERS",
        "Dates" : "DATE_MATCHERS",
        "SSN" : "SSN_MATCHERS",
        "Phone" : "PHONE_MATCHERS",
        "Email" : "EMAIL_MATCHERS",
        "Account Numbers" : "ACCOUNT_MATCHERS",
        "Lab Results" : "LAB_MATCHERS",
        "Allergies" : "ALLERGIES_MATCHERS",
        "ID" : "ID_MATCHERS",
        "Serial Numbers" : "SERIAL_MATCHERS",
        "URLs" : "URL_MATCHERS"
}

regex_phi_dict = {}
regex_phi_dict["All PHI"] = list(regex_match_dict.keys())
regex_phi_dict["PHI Regex 3"] = ["Name", "Address", "Dates", "Phone", "SSN", "Email", "Account Numbers", "ID", "Serial Numbers", "URLs"]
regex_phi_dict["PHI Regex 2"] = ["Name", "Phone", "Date of Birth", "SSN", "Address", "Email", "Allergies", "Lab Results", "Account Numbers"]
regex_phi_dict["PHI Regex 1"] = ["Name", "Address", "Date of Birth", "Phone", "SSN", "Email"]

with open("prompts.yaml", "r") as prompt_file:
   phi_prompts = yaml.safe_load(prompt_file)

# print(phi_prompts)

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

if 'customcode' not in st.session_state:
   st.session_state.customcode = None

if 'encrypted_map' not in st.session_state:
   st.session_state.encrypted_map = None

if 'include_type' not in st.session_state:
   st.session_state.include_type = None

st.header("🧬 Heid: Health Data Deidentifier")

def goDeid():
   st.session_state.state = 0
   st.session_state.input = ""
   st.session_state.output = ""
   st.session_state.reid_map = None
   st.session_state.file = None
   st.session_state.customcode = None
   st.session_state.encrypted_map = None
   st.session_state.method = "LLM"
   st.session_state.phi_no = "All PHI"
   st.rerun()

def goReid():
   st.session_state.state = 3
   st.session_state.input = ""
   st.session_state.output = ""
   st.session_state.reid_map = None
   st.session_state.file = None
   st.session_state.customcode = None
   st.session_state.encrypted_map = None

   st.rerun()
   

if st.session_state.state <= 2 or st.session_state.state > 4:
   if st.sidebar.button("Deidentiy", icon=":material/shuffle:", type="primary"):
      goDeid()
   if st.sidebar.button("Reidentify", icon=":material/fingerprint:", type="secondary"):
      goReid()
      
   st.sidebar.radio("Method", ["LLM", "RegEx"], key = "method")
   if st.session_state.method == "RegEx":
      phi_no = st.sidebar.radio("PHI List", regex_phi_dict.keys(), key="phi_no")
      # phi_no = "Else"
      phi = st.sidebar.multiselect("Select PHI Items to Remove", list(regex_match_dict.keys()), default=regex_phi_dict[phi_no])
   elif st.session_state.method == "LLM":
      phi_no = st.sidebar.radio("PHI List", phi_dict.keys(), key = "phi_no")
      phi = st.sidebar.multiselect("Select PHI Items to Remove", phi_list, default=phi_dict[phi_no])
else:
   if st.sidebar.button("Deidentiy", icon=":material/shuffle:", type="secondary"):
      goDeid()
      
   if st.sidebar.button("Reidentify", icon=":material/fingerprint:", type="primary"):
      goReid()
   

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

def deidentify(include_type = True):
   phiList = []
   with(open("phi2.txt") as phi2):
      phiList = phi2.readlines()

   method = st.session_state.method
   
   # substitute dates using regex
   # covers dates in the form 03/07/2025, 3-7-25, etc.
   if len(st.session_state.input) > 0:
      txt = st.session_state.input

      print(type(txt))
      

      if(method=="RegEx"):
         
         regex_phi_list = [regex_match_dict[i] for i in phi]

         if(phi_no=="PHI 1"):
            # substitute emails using regex

            # print(txt)
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
         
         else:
            print(repr(txt))
            deidentified_ehr, id_map = regex_deidentify(txt, regex_phi_list)
            print(deidentified_ehr, id_map)

            st.session_state.output = deidentified_ehr
            st.session_state.reid_map = str(id_map)


      elif(method=="LLM"):
         prompt = ""
         
         remove_items = [phi_prompts[item] for item in phi]

         
         prompt = """
                  Task: Please anonymize the following clinical note using these instructions:

                  DO NOT ADD OR REMOVE ANY SPACES OR NEWLINE CHARACTERS FROM THE ORIGINAL TEXT.

                  """ + "\n\n".join(remove_items) + """

                  REMOVE INFORMATION WITHOUT ADDING OR REMOVING ANY SPACES OR NEWLINE CHARACTERS.

                  For Example: The string 
                  "Dr. Alex can be called at his phone number:654-123-7777"
                  should become
                  "*name* can be called at his phone number:*phone*"

                  You should only replace personal information and not generic words. For example, if the word 'Name' or 'Phone' appears in the health record, it should NOT be replaced with '*name*' or '*phone*'. ONLY replace words that contain actual personal information.

                  THE OUTPUT SHOULD INCLUDE ONLY THE ANONYMIZED HEALTH RECORD WITH NO OTHER TEXT.

                  Health Record:

                  """ + txt
         
         #print(prompt)

         response = client.models.generate_content(
            model = "gemini-2.0-flash",
            config=types.GenerateContentConfig(
               temperature=0.0
            ),
            contents=[prompt]
         )
         #print(response)
         deid_txt = response.text

         # print(deid_txt)

         deid_ehr, id_map = create_reid_map(txt, deid_txt, st.session_state.include_type)

         st.session_state.output = deid_ehr
         st.session_state.reid_map = str(id_map)


      st.session_state.state = 2

def encrypt():
   st.session_state.encrypted_map = password_encrypt(st.session_state.reid_map, st.session_state.customcode)
   return None
   fernet = Fernet(st.session_state.customcode.encode())
   st.session_state.encrypted_map = fernet.encrypt(st.session_state.reid_map.encode())

def decrypt(code):
   decoded_map = password_decrypt(st.session_state.encrypted_map, st.session_state.customcode)
   st.session_state.reid_map = ast.literal_eval(decoded_map)
   return None
   fernet = Fernet(code.encode())
   decoded_map = fernet.decrypt(st.session_state.encrypted_map).decode()
   st.session_state.reid_map = ast.literal_eval(decoded_map)

if st.session_state.state < 2:
   if st.session_state.state == 0:
      st.subheader("🧮 Deidentify Record")
   if st.session_state.file == None:
      st.session_state.file = st.file_uploader(label = "Upload file here.", type=['txt', 'md'])

      st.write("")
      st.markdown("""**Heid** provides a powerful and intuitive way to safeguard patient privacy by removing Personal Health Information (PHI) from your documents. Whether you're preparing data for research, sharing records securely, or ensuring compliance, you have complete control over the process.

*   **Dual De-identification Methods:** Choose between a high-precision RegEx engine for predictable results or leverage our advanced AI model (LLM) for context-aware detection of sensitive data.
*   **Granular PHI Selection:** Don't settle for a one-size-fits-all approach. Use the sidebar to select exactly which categories of information to remove, from names and addresses to specific medical record numbers.
*   **Secure & Reversible Process:** Your original data is never stored. After de-identification, you can optionally download a password-encrypted re-identification key, allowing you to securely restore the original document whenever you need it.

**Ready to start?** Simply drag and drop your TXT or MD file into the uploader above to begin.

**If you have a deidentified record and want to reidentify please click on the Reidentify tab in the left sidebar.**""")

      
      
   if st.session_state.file is not None:
      if(st.session_state.state==0):
         st.session_state.state = 1
         st.rerun()

      data = st.session_state.file.getvalue()
      stringio = StringIO(data.decode())
      st.session_state.input = stringio.read()
      st.write("")
      st.markdown("""Review your document below. You can adjust your chosen de-identification method (LLM or RegEx) and select which types of information you would like removed in the sidebar.\n
Use LLM for a more robust context-aware removal method, or use traditional RegEx for fast predictable results.\n
Click Deidentify Record to proceed when you are ready.\n
""")
      state = st.button("Deidentify Record", icon=":material/start:", on_click = deidentify)

      if st.session_state.method == "LLM":
         st.session_state.include_type = st.checkbox(label="**Include Info Types in Deidentified Record**", value = True) 
         st.markdown("""> The "Include Info Types" checkbox lets you choose your output format. If checked, personal data is replaced with descriptive type tags like [NAME] or [ADDRESS]. If unchecked, all removed data will be labeled [REMOVED] for maximum privacy.""")
      st.divider()
      
      st.subheader(f"Your Input Record - {st.session_state.file.name}")     

      st.text(st.session_state.input)
      
elif st.session_state.state == 2:

   # PLEASE PUT CODE FOR REIDENTIFICATION HERE

   # to get the ORIGINAL phi, use st.session_state.input
   # to get the DEIDENTIFIED phi, use st.session_state.output
   # if you want any data to persist across streamlit page refreshes, you MUST use st.session_state.var, not just var = data

   # FIRST: we need to figure out which items were actually removed. to do this, iterate over the lines in the deidentified phi, and for every tag like *name*, *date*, etc, look at the same line in the original phi, and find out which characters were removed
   # Put these deidentified items in a dictionary, or write them to a file
   # Take those items and hash them or whatever you need to do for reidentification

   st.subheader("""✅ Process Complete! Record is Now De-identified!""")
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-deidentified.txt"
   
   st.markdown("""Below is a preview of your sanitized document. All selected Personal Health Information (PHI) has been replaced with placeholder tags according to your settings. You can now download this de-identified record for your use.

**Want the ability to reverse this process later?**

The **Re-identification Map** is a secure, encrypted file that acts as the key to restore your original document from this de-identified version.

*   When you click "Get Reidentification Map," you will be prompted to create a password.
*   This password encrypts the map file, making it completely unreadable to anyone without it.
*   To restore the data, you will need three things: the de-identified record, this encrypted map file, and your password.

**Important: We do not store your password or your data.** If you lose your password or the map file, it will be **impossible** to restore the original information. Please store both items in a safe and secure location.""")
   
   st.download_button(label="Download Deidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")

   if(st.session_state.reid_map is not None):
      if(st.button("Get Reidentification Map", icon=":material/key:")):
         st.session_state.state = 5
         st.rerun()
   st.divider()
   st.text(st.session_state.output)
   
elif st.session_state.state == 3:
   st.subheader("📟 Reidentify Record")
   st.markdown("""Have a de-identified record to restore? To begin the re-identification process, please provide the three required items: your de-identified .txt file, your .map key file, and the password you used to encrypt it.
""")
   st.session_state.file = st.file_uploader(label = "Upload DEIDENTIFIED record here.", type=['txt', 'md'])

   st.session_state.reid_map = st.file_uploader(label = "Upload REIDENTIFICATION map here.", type=['map'])

   st.write("")
   st.write("")

   st.markdown("***Please enter the passcode for the reidentification map:***")
   input_password = st.text_input(label="", key="customcode", type="password")

   if input_password and st.session_state.file is not None and st.session_state.reid_map is not None:
      if st.button("Reidentify Record", icon=":material/start:", key="reidentify-enter"):
         try:

            data = st.session_state.file.getvalue()
            stringio = StringIO(data.decode())
            st.session_state.input = stringio.read()

            st.session_state.encrypted_map = st.session_state.reid_map.getvalue()
            # stringio = StringIO(reid_data.decode())
            # st.session_state.encrypted_map = ast.literal_eval(stringio.read())

            decrypt(input_password)

            
            
            
            #data is a string, reid_data is a python dictionary
            st.session_state.output = reidentify(st.session_state.input, st.session_state.reid_map)

         except:
            st.markdown("#### ❌ Reidentification failed. Your passcode may be incorrect.")
         
         else:
            st.session_state.state = 4
            st.rerun()


   
   # if st.session_state.file is not None and st.session_state.reid_map is not None:
   #    if st.button("Reidentify Record"):

   #       data = st.session_state.file.getvalue()
   #       stringio = StringIO(data.decode())
   #       st.session_state.input = stringio.read()

   #       reid_data = st.session_state.reid_map.getvalue()
   #       stringio = StringIO(reid_data.decode())
   #       st.session_state.reid_map = ast.literal_eval(stringio.read())
         
         
   #       #data is a string, reid_data is a python dictionary
   #       st.session_state.output = reidentify(st.session_state.input, st.session_state.reid_map)

   #       st.session_state.state = 4
   #       st.rerun()

elif st.session_state.state == 4:
   st.subheader("""✅ Record Reidentified!""")
   st.markdown("Please review and download your restored record below.")
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-reidentified.txt"
   st.download_button(label="Download Reidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")
   #st.text(st.session_state.input)
   #st.text(str(st.session_state.reid_map))
   st.divider()
   st.text(st.session_state.output)
elif st.session_state.state == 5:
   st.subheader("📑 Get Reidentification Map")
   st.markdown("**To download the reidentification map, please enter or generate a passcode for encryption. You must use this passcode later to reidentify the record. Store it in a safe place.**")

   if "pass_vis" not in st.session_state:
      st.session_state.pass_vis = False

   show_pass = "default" if st.session_state.pass_vis else "password"

   if "gencode" not in st.session_state:
      st.session_state.gencode = None

   if st.button("Generate Random Passcode"):
      key = uuid.uuid4()
      st.session_state.customcode = str(key)
      encrypt()
      print(type(key))
      st.rerun()
   st.write("Generating a random passcode will reset any passcode you have entered below.")

   st.text_input(label="Your Passcode", type=show_pass, key="customcode", on_change=encrypt)

   # st.checkbox(label = "Show Passcode", key="pass_vis", value=False)
   st.write()

   if st.session_state.encrypted_map and st.session_state.customcode is not None and st.session_state.customcode.strip() is not "": #TODO
      reid_download_name = os.path.splitext(st.session_state.file.name)[0] + "-reid_encrypted.map"

      st.download_button(label="Confirm Passcode and Download Map", icon=":material/encrypted:", data=st.session_state.encrypted_map, file_name=reid_download_name, mime="text/plain")
   
      download_name = os.path.splitext(st.session_state.file.name)[0] + "-deidentified.txt"
      st.download_button(label="Download Deidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")


def generate_passcode():
   key = Fernet.generate_key()



phi_counts = dict()
# reid_dict = 

deid_tags = ["name", "date", "phone", "fax", "address", "email", "ssn", "medicaid", "record_no", "health_plan_no", "account_no", "license", "serial", "device", "url", "ip_address", "biometric", "id", "provider", "hospital", "allergies", "lab_results", "medication"]

deid_counts = [1 for tag in deid_tags]

deid_dict_default = dict(zip(deid_tags, deid_counts))

def create_reid_map(txt, deid_txt, include_type = True):
   
   txt = txt.replace("\r\n", "\n").rstrip()
   deid_txt = deid_txt.rstrip()
   # print(repr(txt))
   # print(repr(deid_txt))

   deid_count_dict = copy.deepcopy(deid_dict_default)
   reid_dict = dict()

   new_txt = copy.deepcopy(deid_txt)

   textsearch = dict()

   txt_list = []
   txt_list.append(new_txt)

   for item in deid_count_dict:
      lookfor = "*" + item + "*"
      empty = []
      for substring in txt_list:
         empty += substring.split(lookfor)
      txt_list = empty

   current_start = 0
   deid_iter = 0

   counter = 1

   output = ""

   for i in range(len(txt_list)-1):
      start = txt[current_start:].find(txt_list[i]) + len(txt_list[i]) + current_start
      end = txt[start:].find(txt_list[i+1]) + start
      current_start = end
      # if end == -1:
      #    end = None
      name = txt[start:end]

      deid_start = deid_txt[deid_iter:].find(txt_list[i]) + len(txt_list[i]) + deid_iter
      deid_end = deid_txt[deid_start:].find(txt_list[i+1]) + deid_start
      deid_iter = deid_end
      # if deid_end == -1:
      #    deid_end = None
      deid_type = deid_txt[deid_start+1:deid_end-1]   

      # print(name, deid_type)

      replacement = deid_type.upper()+"#"+str(deid_count_dict[deid_type]) if include_type else "REMOVED#"+str(counter)
      # print(name, deid_type, replacement)
      deid_count_dict[deid_type] += 1
      counter += 1
      output += txt_list[i]
      
      output += "[" + replacement + "]"
      reid_dict[replacement] = name

      

   # print(str(reid_dict))
   output += txt_list[-1]
   
   # print(output)
   # print(str(reid_dict))
   return output, reid_dict
      #start = deid_txt.find(txt_list[i])










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

MATCHER_MAP = {
    "NAME_MATCHERS": [
        (
            r"(Patient name:|Provider name:|Patient:|Provider:|Patient Name:|Provider Name:)\s*((?:" + re_matcher + r"\.\s*)?[A-Z][a-z]+(?:[ ][A-Z][a-z]+)*)",
            "NAME"),
        (r"()(" + re_matcher + r"\.\s*[A-Z][a-z]+(?:[ ][A-Z][a-z]+)*)", "NAME"),
        (r"(Hospital name:|Hospital Name:)\s*(\w+(?: \w+)+)", "HOSPITAL"),
    ],
    "ADDRESS_MATCHERS": [
        (
            r"(Address:)\s*((?:[^,\n]+?)(?:,\s*Apt\s*(?:[^\n,]+?))?(?:,\s*)(?:[^,\n]+?,\s*)?(?:[A-Z]{2})\s*(?:\d{5}(?:-\d{4})?))",
            "ADDRESS"),
    ],
    "DOB_MATCHERS": [
        (r"(Date of Birth:|DoB:|DOB:)\s*(\d{2}/\d{2}/\d{4})", "DOB"),
    ],
    "DATE_MATCHERS": [
       (r"(\s*)(\d{2}/\d{2}/\d{4})", "DATE"),
    ],
    "SSN_MATCHERS": [
        (r"(SSN:)\s*([0-9*]{3}-[0-9*]{2}-[0-9*]{4})", "SSN"),
    ],
    "PHONE_MATCHERS": [
        (r"(Phone:)\s*(\d{3}-\d{3}-\d{4})", "PHONE"),
        (r"(Fax number:|Fax no\.:)\s*(\d{3}-\d{3}-\d{4})", "NUMBER"),
    ],
    "EMAIL_MATCHERS": [
        (r"(email:|Email:)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", "EMAIL"),
    ],
    "ACCOUNT_MATCHERS": [
        (r"(Medicaid account:|Account:)\s*(\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b)", "ACCOUNT"),
    ],
    "LAB_MATCHERS": [
        (r"(Lab Results\s*(?:\((?:[0-1]?[0-9]/[0-3]?[0-9]/\d{4})\))?:)\s*((?:\n-\s*.+)+)", "LAB"),
        (r"(Lab Results\s*(?:\((?:[0-1]?[0-9]/[0-3]?[0-9]/\d{4})\))?:)((?:\n-?\s(?!Follow+).+)+)", "LAB"),
    ],
    "ALLERGIES_MATCHERS": [
        (r"(Allergies:)((?:\n-?\s(?![\w ]+:).+)+)", "ALLERGIES"),
    ],
    "ID_MATCHERS": [
        (r"(Health plan beneficiary number:)\s*(\d{3}-\d{4}-\d{4})", "NUMBER"),
        (r"(Medical record number:)\s*([A-Za-z0-9]{7}-[A-Za-z0-9]{7})", "NUMBER"),
        (r"(license number:)\s*([A-Za-z0-9]{4}-[A-Za-z0-9]{6})", "NUMBER"),
        (r"(Certificate number:)\s*([A-Za-z0-9]{6}-[A-Za-z0-9]{4})", "NUMBER"),
        (r"(Health Insurance:)\s*([A-Za-z0-9]{5}-[A-Za-z0-9]{10})", "NUMBER"),
        (r"(Group no\.:)\s*(\d{6})", "NUMBER"),
        (r"(Code:)\s*(\d+)", "NUMBER"),
    ],
    "SERIAL_MATCHERS": [
        (r"(Device identifier:)\s*([A-Za-z0-9]{6}-[A-Za-z0-9]{8})", "NUMBER"),
        (r"(Pacemaker serial numbers:)\s*([A-Za-z0-9]{5}-[A-Za-z0-9]{7})", "NUMBER"),
    ],
    "URL_MATCHERS": [
        (
            r"(URL:)\s*((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\))+(?:\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))",
            "URL"),
    ]
}


# De-identifies EHR text by iteratively replacing only the sensitive information to keep track of what was replaced.
def deidentify_ehr_iterative_selective(text, patterns: list[tuple] = []):
    replaced_counts = {}
    de_id_map = {}
    updated_text = text

    # cant deidentify if no matchers are passed
    if len(patterns) == 0:
        return updated_text, de_id_map

    previous_text = None
    while previous_text != updated_text:
        previous_text = updated_text
        for pattern, prefix in patterns:
            updated_text, replaced_counts = replace_with_unique_identifier_iterative_selective(
                updated_text, pattern, prefix, replaced_counts, de_id_map
            )

    return updated_text, de_id_map


def reidentify_ehr(text, id_map):
    # This regex matches [TYPE#123] format
    pattern = re.compile(r"\[(\w+#\d+)\]")

    def replace(match):
        # drop the brackets
        # try to replace this token using the id_map
        # if it’s not in the map, just leave the token as is
        key = match.group(1)
        return id_map.get(key, match.group(0))

    return pattern.sub(replace, text)

def regex_deidentify(txt, regex_list):
   txt = txt.replace("\r\n", "\n").rstrip()
   matcher_list = []
   
   for category in regex_list:
      matcher_list += MATCHER_MAP[category]

   deidentified_ehr, id_map = deidentify_ehr_iterative_selective(txt, matcher_list)
   return deidentified_ehr, id_map



# with(open("ehr JMS.txt") as phi2):
#     ehr_text = ''.join(list(phi2.readlines()))

#     matcher_list = []
#     for category in [
#         "NAME_MATCHERS",
#         "ADDRESS_MATCHERS",
#         "DOB_MATCHERS",
#         "SSN_MATCHERS",
#         "PHONE_MATCHERS",
#         "EMAIL_MATCHERS",
#         "ACCOUNT_MATCHERS",
#         "LAB_MATCHERS",
#         "ALLERGIES_MATCHERS",
#         "ID_MATCHERS",
#         "SERIAL_MATCHERS",
#         "URL_MATCHERS"
#     ]:
#         matcher_list += MATCHER_MAP[category] or []

#     # Apply the selective iterative de-identification function
#     deidentified_ehr, id_map = deidentify_ehr_iterative_selective(ehr_text, matcher_list)
#     print(deidentified_ehr, id_map)

#     # prin reidentified text
#     reidentified_text = reidentify_ehr(deidentified_ehr, id_map)
#     print(reidentified_text)