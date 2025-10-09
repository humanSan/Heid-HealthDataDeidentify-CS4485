import re
import streamlit as st
import tempfile
from matchers.addresses import strip_addresses
from matchers.dates import strip_dates
from matchers.emails import strip_emails
from matchers.names import strip_names
from matchers.phonenums import strip_phone_nums
from matchers.ssn import strip_ssn

st.header("Deidentify Health Record")

user_file = st.file_uploader(label = "Max file size **200 MB**.\nSupported Types:\ntxt", type=['txt'])

with tempfile.TemporaryFile() as temp:
        temp.write(user_file.getbuffer())
        filename=user_file.name

        txt = temp.read()
        
        txt = strip_dates(txt)
        txt = strip_emails(txt)
        txt = strip_phone_nums(txt)
        txt = strip_names(txt)
        txt = strip_ssn(txt)
        txt = strip_addresses(txt)

        st.text(txt)

        st.download_button(label="Download Deidentified Record", data=txt, file_name=""+filename+".txt", mime="text/plain")

