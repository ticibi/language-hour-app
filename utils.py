import streamlit as st
import pandas as pd
from io import BytesIO

def initialize_session_state(vars):
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Sheet1")
    writer.save()
    data = output.getvalue()
    return data
