import streamlit as st
import base64

def display_file(filename):
    with open(f'temp/{filename}', "rb") as f:
        pdf = base64.b64encode(f.read()).decode('utf-8')
    html = f'<embed src="data:application/pdf;base64,{pdf}" width="700" height="900" type="application/pdf">'
    st.markdown(html, unsafe_allow_html=True)
