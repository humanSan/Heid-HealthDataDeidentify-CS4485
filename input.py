import streamlit as st

def update(text):
    st.write("The current movie title is", text)


title = st.text_input("Movie title", on_change=update)


