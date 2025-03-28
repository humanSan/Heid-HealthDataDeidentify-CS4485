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
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

st.set_page_config(
        page_title="DeIdentify Health Info",
)

method = st.sidebar.radio("Method", ["LLM", "RegEx"])

if 'state' not in st.session_state:
   st.session_state.state = 0

if 'input' not in st.session_state:
   st.session_state.input = ""

if 'output' not in st.session_state:
   st.session_state.output = ""

if 'file' not in st.session_state:
   st.session_state.file = None

st.header("Deidentification of Health Data")

if st.session_state.file == None:
   st.session_state.file = st.file_uploader(label = "Upload file here.", type=['txt', 'md'])

def deidentify():
   phiList = []
   with(open("phi2.txt") as phi2):
      phiList = phi2.readlines()
   
   # substitute dates using regex
   # covers dates in the form 03/07/2025, 3-7-25, etc.
   if len(st.session_state.input) > 0:
      txt = st.session_state.input

      if(method=="RegEx"):
         # substitute emails using regex
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
      elif(method=="LLM"):
         
         prompt = """
                  Task: Please anonymize the following clinical note using these instructions:
                  
                  Replace the names and acronyms, initials, including honorifics like Ms, Mr, Dr, and MD of doctor names, patient names with the string '*name*'
                  Replace any names of social workers or health workers with the string '*name*'
                  Replace any locations or addresses such as "3970 Longview Drive, York, PA" with the string '*address*'
                  Replace any dates of birth with the string '*dob*'
                  Repace any SSN or Social Security Information with '*ssn*'
                  Replace clinic and hospital names with the string '*hospital*'
                  Replace each lab result and the type of the lab result in the lab results section with the string '*lab_results*'
                  Replace each allergy in the allergies section with the string '*allergy*'
                  Replace each email address with the string '*email*'
                  Replace any Medicaid account information with the string '*medicaid*'
                  Replace each provider name with the string '*provider*'
                  Replace each phone number with the string '*phone*'

                  An example: The sentence "Dr. Alex can be called at 654-123-7777" should become "*name* can be called at *phone*.

                  You should only replace personal information and not generic words. For example, if the word 'name' or 'phone' appears in the health record, it should NOT be replaced with '*name*' or '*phone*'. Do NOT replace words that are actual personal information
                  
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
else:
   st.markdown("""### Record Deidentified!""")
   st.text(st.session_state.output)
   st.download_button(label="Download Deidentified Record", data=st.session_state.output, file_name=""+st.session_state.file.name+"-deidentified.txt", mime="text/plain")


