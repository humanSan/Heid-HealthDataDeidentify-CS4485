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

load_dotenv()
client = genai.Client()

st.set_page_config(
        page_title="DeIdentify Health Info",
)



phi_list = ["Doc Name", "Patient Name", "All Names", "Social Worker Names", "Date of Birth", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medicaid Account", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code", "Provider Name", "Hospital Name", "Allergies", "Lab Results"]

phi_dict = {}

phi_dict["All PHI"] = phi_list

phi_dict["PHI List 3"] = ["All Names", "All Dates", "Phone Number", "Fax Number", "Address", "Email", "SSN", "Medical Record Number", "Health Plan Beneficiary Number", "All Account Numbers", "Certificate/License Number", "Serial Number", "Device Identifier", "URL", "IP Address", "Biometric Identifier", "Unique ID or Code"]

phi_dict["PHI List 2"] = ["Patient Name", "Doc Name", "Date of Birth", "SSN", "Address", "Email", "Provider Name", "Hospital Name", "Allergies", "Lab Results", "Medicaid Account", "Social Worker Names", "Phone Number"]



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

st.header("🧬 Health Data Deidentifier")

if st.session_state.state <= 2 or st.session_state.state > 4:
   if st.sidebar.button("Reidentify", icon=":material/fingerprint:", type="primary"):
      st.session_state.state = 3
      st.session_state.input = ""
      st.session_state.output = ""
      st.session_state.reid_map = None
      st.session_state.file = None
      st.session_state.customcode = None
      st.session_state.encrypted_map = None

      st.rerun()
   method = st.sidebar.radio("Method", ["LLM", "RegEx"])
   if method == "RegEx":
      phi_no = st.sidebar.radio("PHI List", ["PHI 1", "PHI 3"], index=0)
   elif method == "LLM":
      phi_no = st.sidebar.radio("PHI List", phi_dict.keys(), index=0)
      phi = st.sidebar.multiselect("Select PHI Items to Remove", phi_list, default=phi_dict[phi_no])
else:
   if st.sidebar.button("Deidentiy", icon=":material/shuffle:", type="primary"):
      st.session_state.state = 0
      st.session_state.input = ""
      st.session_state.output = ""
      st.session_state.reid_map = None
      st.session_state.file = None
      st.session_state.customcode = None
      st.session_state.encrypted_map = None
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

                  DO NOT ADD OR REMOVE ANY SPACES OR NEWLINE CHARACTERS FROM THE ORIGINAL TEXT.

                  """ + "\n".join(remove_items) + """

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

         deid_ehr, id_map = create_reid_map(txt, deid_txt)

         st.session_state.output = deid_ehr
         st.session_state.reid_map = str(id_map)


      st.session_state.state = 2

iterations = 100_000

def derive_key(password: bytes, salt: bytes) -> bytes:
    """Derive a secret key from a given password and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), 
        length=32, 
        salt=salt,
        iterations=iterations, 
        backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password))

def password_encrypt(text: str, password: str) -> bytes:
    salt = secrets.token_bytes(16) # Generate a salt
    key = derive_key(password.encode(), salt) #enccode password as utf, send it to derive key, which generates a password in non base64, encodes it as b64 and returns it
    encoded = text.encode()
    return base64.urlsafe_b64encode(
        b'%b%b%b' % (
            salt,
            iterations.to_bytes(4, 'big'),
            base64.urlsafe_b64decode(Fernet(key).encrypt(encoded)),
        )
    )

def password_decrypt(encrypted_data: bytes, password: str) -> str:
    decoded = base64.urlsafe_b64decode(encrypted_data) # returns non base64 bytes
    salt, iter, encrypted_txt = decoded[:16], decoded[16:20], base64.urlsafe_b64encode(decoded[20:])
    iterations = int.from_bytes(iter, 'big')
    key = derive_key(password.encode(), salt)
    return Fernet(key).decrypt(encrypted_txt).decode()


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
      
   if st.session_state.file is not None:
      if(st.session_state.state==0):
         st.session_state.state = 1
         st.rerun()

      data = st.session_state.file.getvalue()
      stringio = StringIO(data.decode())
      st.session_state.input = stringio.read()
      st.write("")
      st.subheader(f"Your Input Record - {st.session_state.file.name}")
      state = st.button("Deidentify Record", icon=":material/start:", on_click = deidentify)
      st.write("")
      st.text(st.session_state.input)
      
elif st.session_state.state == 2:

   # PLEASE PUT CODE FOR REIDENTIFICATION HERE

   # to get the ORIGINAL phi, use st.session_state.input
   # to get the DEIDENTIFIED phi, use st.session_state.output
   # if you want any data to persist across streamlit page refreshes, you MUST use st.session_state.var, not just var = data

   # FIRST: we need to figure out which items were actually removed. to do this, iterate over the lines in the deidentified phi, and for every tag like *name*, *date*, etc, look at the same line in the original phi, and find out which characters were removed
   # Put these deidentified items in a dictionary, or write them to a file
   # Take those items and hash them or whatever you need to do for reidentification

   st.subheader("""✅ Record Deidentified!""")
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-deidentified.txt"
   st.download_button(label="Download Deidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")

   if(st.session_state.reid_map is not None):
      if(st.button("Get Reidentification Map", icon=":material/key:")):
         st.session_state.state = 5
         st.rerun()
   st.text(st.session_state.output)
   
elif st.session_state.state == 3:
   st.subheader("📟 Reidentify Record")
   st.session_state.file = st.file_uploader(label = "Upload DEIDENTIFIED record here.", type=['txt', 'md'])

   st.session_state.reid_map = st.file_uploader(label = "Upload REIDENTIFICATION map here.", type=['map'])

   st.write("")
   st.write("")

   st.markdown("##### Please enter the passcode for the reidentification map:")
   input_password = st.text_input(label="", key="customcode", type="password")

   if input_password and st.session_state.file is not None and st.session_state.reid_map is not None:
      if st.button("Reidentify Record", icon=":material/start:", key="reidentify-enter"):
         # try:

         data = st.session_state.file.getvalue()
         stringio = StringIO(data.decode())
         st.session_state.input = stringio.read()

         st.session_state.encrypted_map = st.session_state.reid_map.getvalue()
         # stringio = StringIO(reid_data.decode())
         # st.session_state.encrypted_map = ast.literal_eval(stringio.read())

         decrypt(input_password)

         
         
         
         #data is a string, reid_data is a python dictionary
         st.session_state.output = reidentify(st.session_state.input, st.session_state.reid_map)

         # except:
         #    st.markdown("## Reidentification Failed. Your passcode may be incorrect.")
         
         # else:
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
   download_name = os.path.splitext(st.session_state.file.name)[0] + "-reidentified.txt"
   st.download_button(label="Download Reidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")
   #st.text(st.session_state.input)
   #st.text(str(st.session_state.reid_map))
   st.text(st.session_state.output)
elif st.session_state.state == 5:
   st.subheader("📑 Get Reidentification Map")
   st.markdown("**To download the reidentification map, please generate a passcode for encryption. You must *use* this passcode later to reidentify the record. Store it in a safe place.**")

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
   st.write("Generating a passcode will reset any passcode you have entered below")

   st.text_input(label="Your Passcode", type=show_pass, key="customcode", on_change=encrypt)

   # st.checkbox(label = "Show Passcode", key="pass_vis", value=False)
   st.write()

   if st.session_state.encrypted_map:
      reid_download_name = os.path.splitext(st.session_state.file.name)[0] + "-reid_encrypted.map"

      st.download_button(label="Confirm Passcode and Download Map", icon=":material/encrypted:", data=st.session_state.encrypted_map, file_name=reid_download_name, mime="text/plain")
   
      download_name = os.path.splitext(st.session_state.file.name)[0] + "-deidentified.txt"
      st.download_button(label="Download Deidentified Record", icon=":material/download:", data=st.session_state.output, file_name=download_name, mime="text/plain")


def generate_passcode():
   key = Fernet.generate_key()



phi_counts = dict()
# reid_dict = 

deid_tags = ["name", "dob", "date", "phone", "fax", "address", "email", "ssn", "medicaid", "record_no", "health_plan_no", "account_no", "license", "serial", "device", "url", "ip_address", "biometric", "id", "provider", "hospital", "allergies", "lab_results"]

deid_counts = [1 for tag in deid_tags]

deid_dict_default = dict(zip(deid_tags, deid_counts))

def create_reid_map(txt, deid_txt):
   
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
   
   print(txt_list)
   print()
   print(repr(txt))
   print()
   print(repr(deid_txt))

   current_start = 0
   deid_iter = 0

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

      replacement = deid_type.upper()+"#"+str(deid_count_dict[deid_type])
      print(name, deid_type, replacement)
      deid_count_dict[deid_type] += 1
      output += txt_list[i]
      
      output += "[" + replacement + "]"
      reid_dict[replacement] = name

      

   print(str(reid_dict))
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
        (r"(Lab Results\s*(?:\((?:[0-1]?[0-9]/[0-3]?[0-9]/\d{4})\))?:)\s*((?:\n-\s*.+)+)", "LAB"),
        (r"(Allergies:)((?:\n-?\s(?![\w ]+:).+)+)", "ALLERGIES"),
        (r"(Lab Results\s*(?:\((?:[0-1]?[0-9]/[0-3]?[0-9]/\d{4})\))?:)((?:\n-?\s(?!Follow+).+)+)", "LAB"),
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