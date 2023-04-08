import streamlit as st
import pandas as pd
from io import BytesIO
from time import time
from PyPDF2 import PdfWriter, PdfReader
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject
import PyPDF2.generic as pdfgen
from config import SESSION_VARIABLES
from datetime import datetime, date
from sqlalchemy import func
from models import LanguageHour, User, Group, File, Score, Course

def get_user_monthly_hours(db, user_id):
    current_month = date.today().month
    current_year = date.today().year
    total_hours = db.query(func.sum(LanguageHour.hours)).\
        filter(LanguageHour.user_id == user_id).\
        filter(func.extract('month', LanguageHour.date) == current_month).\
        filter(func.extract('year', LanguageHour.date) == current_year).scalar() or 0
    return total_hours

def get_user_monthly_hours_required(db, user_id):
    result = db.query(Score).filter(Score.user_id == user_id).first()
    if not result:
        return 0
    l = result.listening
    r = result.reading

    if l in ['0', '0+', '1', '1+'] and r in ['0', '0+', '1', '1+']:
        return 12
    elif (l == '2' and r in ['2', '2+']) or (r == '2' and l in ['2', '2+']):
        return 8
    elif (l in ['2', '2+'] and r in ['2+', '3']) or (l in ['2', '2+'] and r in ['2+', '3']):
        return 6
    elif l in ['3', '3+', '4'] and r in ['3', '3+', '4']:
        return 4
    else:
        return 0
    
class dot_dict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

def initialize_session_state_variables(vars=SESSION_VARIABLES):
    '''helper function to initialize streamlit session state variables'''
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def to_excel(df):
    '''convert dataframe into downloadable excel file'''
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name="MyHistory")
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

