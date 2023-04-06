import streamlit as st
import pandas as pd
import pytz
from io import BytesIO
from time import time
from datetime import datetime
import config
from PyPDF2 import PdfWriter, PdfReader
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject
import PyPDF2.generic as pdfgen

def initialize_session_state_variables(vars):
    '''helper function to initialize streamlit session state variables'''
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def to_excel(df):
    '''convert dataframe into downloadable excel file'''
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="MyHistory")
    writer.save()
    return output.getvalue()

def timeit(func):
    '''time how long a function takes to execute'''
    def wrapper(*args, **kwargs):
        start = time()
        output = func(*args, **kwargs)
        stop = time()
        print(func.__name__, "executed in", int((stop - start) * 1000), "ms")
        return output
    return wrapper

def calculate_hours_done_this_month(data, month=datetime.now().date().month):
    # if member has no entries
    if not isinstance(data, pd.core.frame.DataFrame):
        return 0
    if data is None:
        return 0
    # get sum of hours done during the month
    hours = sum([int(row[1]) for row in data.values if int(row[0][5:7]) == month])
    return hours

def calculate_hours_required(data: dict) -> int:
    if not data or data is None:
        return 0

    def _eval(_string: str):  
        value = 0.0
        if '+' in _string:
            value += 0.5
            _string = _string.strip('+')
            value += float(_string)
        else:
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
        
    # if score is 3+
    if listen in GOOD and read in GOOD:
        return 0

    # if score is 2
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
    '''get the index of the row where user data is located'''
    df = st.session_state.members
    index = df.loc[df['Name'] ==  name].index[0]
    return index + 1

def check_due_dates(scores: dict) -> tuple:
    '''return range as timestamp tuple (DLPT due date, SLTE due date)'''
    str_format = '%m/%d/%Y'
    one_year = 31536000.0
    one_month = 2628000.0

    listen = scores[config.CLANG_L].strip("+")
    read = scores[config.CLANG_R].strip("+")

    if scores[config.DLTP_DATE] != '':
        last_dlpt = datetime.strptime(scores[config.DLTP_DATE], str_format).timestamp()
    else:
        last_dlpt = -1

    if scores[config.SLTE_DATE] != '':
        last_slte = datetime.strptime(scores[config.SLTE_DATE], str_format).timestamp()
    else:
        last_slte = -1

    def calculate_next_dlpt_date(last_date):
        '''returns next due date as timestamp'''
        _next_dlpt = last_date
        if last_date == -1:
            return -1
        if int(listen) >= 3 and int(read) >= 3:
            _next_dlpt = last_date + one_year * 2
        
        elif int(listen) >= 2 and int(read) >= 2:
            _next_dlpt = last_date + one_year

        elif int(listen) < 2 and int(read) < 2:
            _next_dlpt = last_date + one_year
        return _next_dlpt
    
    def calculate_next_slte_date(last_date):
        '''returns next due date as timestamp'''
        _next_slte = last_date
        if last_date == -1:
            return -1
        if int(listen) >= 3 and int(read) >= 3:
            _next_slte = last_date + one_month * config.SLTE_RANGE['3']
        
        elif int(listen) >= 2 and int(read) >= 2:
            _next_slte = last_date + one_month * config.SLTE_RANGE['2']

        elif int(listen) < 2 and int(read) < 2:
            _next_slte = last_date + one_month * config.SLTE_RANGE['1']
        return _next_slte

    next_dlpt = calculate_next_dlpt_date(last_dlpt)
    next_slte = calculate_next_slte_date(last_slte)
    
    return (next_dlpt, next_slte)

def to_date(bignumber):
    '''convert timestamp to EST date'''
    return datetime.fromtimestamp(bignumber, tz=pytz.timezone('US/Eastern')).strftime('%m/%Y')

def set_need_appearances_writer(writer: PdfWriter):
    # See 12.7.2 and 7.7.2 for more information: http://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
    try:
        catalog = writer._root_object
        # get the AcroForm tree
        if "/AcroForm" not in catalog:
            writer._root_object.update({
                NameObject("/AcroForm"): IndirectObject(len(writer._objects), 0, writer)
            })

        need_appearances = NameObject("/NeedAppearances")
        writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
        # del writer._root_object["/AcroForm"]['NeedAppearances']
        return writer

    except Exception as e:
        print('set_need_appearances_writer() catch : ', repr(e))
        return writer

def create_pdf(data):
    reader = PdfReader('template.pdf')
    page = reader.pages[0]

    writer = PdfWriter()
    set_need_appearances_writer(writer)

    fields = reader.get_fields()
    key = pdfgen.NameObject('/V')
    value = pdfgen.create_string_object('TESTVALUE')
    fields['Member Name'][key] = value

    writer.update_page_form_field_values(page, fields=data)
    writer.add_page(page)

    # Save the output PDF file to a buffer
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)

    return output_buffer

