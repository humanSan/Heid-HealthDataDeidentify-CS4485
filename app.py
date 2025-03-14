import os
from io import StringIO
import streamlit as st
import re
from matchers.addresses import strip_addresses
from matchers.dates import *
from matchers.emails import strip_emails
from matchers.names import strip_names
from matchers.phonenums import strip_phone_nums
from matchers.ssn import strip_ssn


# client = genai.Client()

st.set_page_config(
        page_title="DeIdentify Health Info",
)

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
   st.session_state.file = st.file_uploader(label = "Upload file here.", type=['txt', 'md', 'py'])

def deidentify():
   # substitute dates using regex
   # covers dates in the form 03/07/2025, 3-7-25, etc.
   if len(st.session_state.input) > 0:
      txt = st.session_state.input

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


