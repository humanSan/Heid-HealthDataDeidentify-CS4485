import os
from io import StringIO
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types
import re

load_dotenv()

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

if st.session_state.state == 0:
   st.session_state.file = st.file_uploader(label = "Upload file here.", type=['txt', 'md', 'py'])

def deidentify():
   # substitute dates using regex
   # covers dates in the form 03/07/2025, 3-7-25, etc.
   if len(st.session_state.input) > 0:
      txt = st.session_state.input

      txt = re.sub(r"\d{1,2}([\/-])\d{1,2}\1\d{2,4}", "*date*", txt)

      # substitute emails using regex
      txt = re.sub(r"[\w.%+-]+@[\w.]+\.[A-Za-z]+", "*email*", txt)

      # substitute phone numbers using regex
      # works only for 10-digit numbers with optional +1
      txt = re.sub(r"(\+1\s*)?\(?(\d{3})\)?\s*-?\d{3}-?\s*\d{4}", "*phonenum*", txt)

      from matchers.names import strip_names
      txt = strip_names(txt)


      # ssn
      txt = re.sub(r"\d{3}[-]\d{2}[-]\d{4}", "*ssn*", txt)


      # street-address
      txt = re.sub(r"\b(\d{1,5}(\s\w+)+),([ -]([A-Z][a-z]+|\d+[A-Za-z]))+([, -]+([A-Z][a-z]+|[A-Z]{2,3}))*([, -]+(\d{4,6}))+([, -]+([A-Z][a-z]+|[A-Z]{2,3}))*", "*address*", txt)

      st.session_state.output = txt

      st.session_state.state = 2

if st.session_state.state < 2:
   if st.session_state.file is not None:
      st.session_state.state = 1
      data = st.session_state.file.getvalue()
      stringio = StringIO(data.decode())
      st.session_state.input = stringio.read()
      st.write("")
      st.markdown("### Your Input Record:")
      st.text(st.session_state.input)
      st.write("")
      state = st.button("Deidentify Record", on_click = deidentify)
else:
   st.markdown("""---
   ### Record Deidentified!""")
   st.text(st.session_state.output)
   st.download_button(label="Download Deidentified Record", data=st.session_state.output, file_name=""+st.session_state.file.name+".txt", mime="text/plain")


