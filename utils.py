import streamlit as st
import pandas as pd
from io import BytesIO
from time import time
from datetime import datetime
import config


def initialize_session_state_variables(vars):
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="MyHistory")
    writer.save()
    return output.getvalue()

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

def calculate_hours_required(data: dict) -> int:
    if not data or data is None:
        return 0

    def _eval(_string: str):
            if _string not in BAD + OKAY + GOOD:
                return
  
            value = 0.0
            if '+' in _string:
                value += 0.5
                _string = _string.strip('+')
                value += float(_string)
            value = float(_string)
            return value

    BAD = ['1+', '1', '0+', '0']
    OKAY = ['2', '2+']
    GOOD = ['3', '3+', '4']

    listen = data[config.CLANG_L]
    read = data[config.CLANG_R]

    # if either score is below 2
    if listen in BAD or read in BAD:
        return 12
        
    # if someone has a 3/3 or higher
    if listen in GOOD and read in GOOD:
        return 0

    # if someone has a 2
    else:
        table ={
            5.5: 2,
            5.0: 4,
            4.5: 6,
            4.0: 8
        }
        l_value = _eval(listen)
        r_value = _eval(read)
        return table[l_value + r_value]


def get_user_info_index(name):
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

def check_due_date(scores: dict) -> tuple:
    '''
    Return date range as tuple
    dlpt date range 3mo before due month - due month
    slte date range 3mo before min (12mo) - 6mo before max (2/2 - 18mo, 3/3 - 36mo, under 2 - 12mo)

    Fx reads 2 columns (CLang-L and CLang-R)
    if 3/3 then dlpt due date range = (lastDLPT + 21mo) to (lastDLPT + 24mo)
        and slte due date range = (lastSLTE + 9mo) to (lastSLTE + 36mo)
    else dlpt due date range = (lastDLPT + 9mo) to (lastDLPT + 12mo)
        and slte due date range = (lastSLTE + 9mo) to (lastSLTE + 18mo)
    '''
    str_format = '%m/%d/%Y'
    year = 31536000.0
    month = 2628000.0
    if not scores['DLPT Date']:
        dlpt_last = None
    else:
        dlpt_last = datetime.strptime(scores['DLPT Date'], str_format).timestamp()

    if not scores['SLTE Date']:
        slte_last = None
    else:
        slte_last = datetime.strptime(scores['SLTE Date'], str_format).timestamp()
        
    
    if scores['CLang'] in ['AD']:
        if scores['MSA - Listening'] == '3' and ['MSA - Reading'] == '3':
            dltp_due = dlpt_last + (year * 2) if slte_last is not None else dlpt_last
            slte_due = slte_last + (year * 2) if slte_last is not None else slte_last
        else:
            dltp_due = dlpt_last + year if slte_last is not None else dlpt_last
            slte_due = slte_last + (year + (month * 6)) if slte_last is not None else slte_last
    elif scores['CLang'] in ['AP', 'DG']:
        if scores['CL - Listening'] == '3' and ['MSA - Reading'] == '3':
            dltp_due = dlpt_last + (year * 2) if slte_last is not None else dlpt_last
            slte_due = slte_last + (year * 2) if slte_last is not None else slte_last
        else:
            dltp_due = dlpt_last + year if slte_last is not None else dlpt_last
            slte_due = slte_last + (year + (month * 6)) if slte_last is not None else slte_last
            
    output = (str(datetime.fromtimestamp(dltp_due))[:10], str(datetime.fromtimestamp(slte_due))[:10])
    return output
    
    
    
