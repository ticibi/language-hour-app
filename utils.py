import streamlit as st
import pandas as pd
from io import BytesIO
from time import time
from datetime import datetime


def initialize_session_state_variables(vars):
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def to_excel(df):
    #output = BytesIO()
    #writer = pd.ExcelWriter(output, engine="xlsxwriter")
    file = df.to_excel('LanguageHourHistory', sheet_name="Sheet1")
    return file

def timeit(func):
    def wrapper(*args, **kwargs):
        start = time()
        output = func(*args, **kwargs)
        stop = time()
        print(func.__name__, "executed in", int((stop - start) * 1000), "ms")
        return output
    return wrapper

def calculate_hours_done_this_month(service, name, month=datetime.now().date().month):
    try:
        data = service.sheets.get_data(columns=['Date', 'Hours'], worksheet_id=st.session_state.config['HourTracker'], tab_name=name)
    except Exception as e:
        print(e)
        return 0
    if data is None:
        return 0
    hours = sum([int(d[1]) for d in data.values if int(d[0][5:7]) == month])
    return hours

def calculate_hours_required(data):
    if data is None:
        return 0
    def to_value(score:str):
        total: float = 0.0
        if '+' in score:
            total =+ 0.5
            score = score.replace('+', '')
        total += float(score)
        return total

    def evaluate(score:float):
        value: int = 0
        match score:
            case '5.5': 
                value = 2,
            case '5.0': 
                value = 4,
            case '4.5': 
                value = 6,
            case '4.0': 
                value = 8,
            case _:
                if float(score) >= 6:
                    value = 0
                elif float(score) < 4:
                    value = 12
        return value

    def highest(scores:list, k=2):
        if k > len(scores):
            raise ValueError
        values = sorted(scores, reverse=True)
        return values[:k]
    
    BAD = ['1+', '1', '0+', '0']
    GOOD = ['3', '3+', '4']

    if isinstance(data, pd.DataFrame):
        if data.empty:
            return 0

    if isinstance(data, dict):
        if not data:
            return 0

    if data['CLang'] == 'AD':
        if data['MSA - Listening'] in GOOD and data['MSA - Reading'] in GOOD:
            return 0
        if data['MSA - Listening'] in BAD or data['MSA - Reading'] in BAD:
            return 12
        else:
            value = sum([to_value(data['MSA - Listening']), to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]

    if data['CLang'] in ['AP', 'DG']:
        if data['CL - Listening'] in GOOD and data['MSA - Reading'] in GOOD:
            return 0
        if data['Dialects']:
            vals = [v.strip().split(' ')[1] for v in data['Dialects'].split(',')]
            vals.append(data['CL - Listening'])
            high = to_value((highest(vals, 1)[0]))
            value = sum([high, to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
        else:
            if data['CL - Listening'] in BAD or data['MSA - Reading'] in BAD:
                return 12
            value = sum([to_value(data['CL - Listening']), to_value(data['MSA - Reading'])])
            return evaluate(str(value))[0]
    else:
        return 999

def get_user_info_index(name):
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

