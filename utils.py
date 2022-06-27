import streamlit as st
import pandas as pd
from io import BytesIO
from time import time


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

def timeit(func):
    def wrapper(*args, **kwargs):
        start = time()
        output = func(*args, **kwargs)
        stop = time()
        print(func.__name__, "executed in", int((stop - start) * 1000), "ms")
        return output
    return wrapper
