import streamlit as st
import pandas as pd
from io import BytesIO
from time import time
from PyPDF2 import PdfWriter, PdfReader
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject
import PyPDF2.generic as pdfgen
from config import SESSION_VARIABLES
from models import LanguageHour
import calendar
from datetime import datetime


def spacer(cols, len=1):
    for i in range(len):
        cols.write(' ')
    return

def divider():
    st.markdown('''---''')


class dot_dict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __getstate__(self):
        return self.copy()

    def __setstate__(self, state):
        self.update(state)

    def __reduce__(self):
        items = tuple(self.items())
        inst_dict = vars(self).copy()
        inst_dict.pop('__dict__', None)
        inst_dict.pop('__weakref__', None)
        return self.__class__, (items,), inst_dict

    def __repr__(self):
        return f"dot_dict({super().__repr__()})"
    
    def to_dict(self):
        return {k: v for k, v in self.items() if k != "_sa_instance_state"}

def language_hour_history_to_string(history):
    output_string = ''
    for row in history:
        output_string += f'{str(row.date.day)} {str(calendar.month_abbr[int(row.date.month)])}' + ' - ' + str(row.hours) + ' hrs - ' + str(row.description) + '\n'
    return output_string

def filter_monthly_hours(data, month, year):
    filtered_data = []
    for item in data:
        date = datetime.strptime(str(item.date), '%Y-%m-%d').date()
        if date.month == month and date.year == year:
            filtered_data.append(item)
    return filtered_data

def calculate_total_hours(filtered_data):
    total_hours = 0
    for data in filtered_data:
        total_hours += data.hours
    return total_hours

def calculate_required_hours(score_data):
    listening = score_data.listening
    reading = score_data.reading
    if listening in ['0', '0+', '1', '1+'] and reading in ['0', '0+', '1', '1+']:
        return 12
    elif (listening == '2' and reading in ['2', '2+']) or (reading == '2' and listening in ['2', '2+']):
        return 8
    elif (listening in ['2', '2+'] and reading in ['2+', '3']) or (listening in ['2+', '3'] and reading in ['2', '2+']) or (listening in ['3'] and reading in ['2+']) or (listening in ['2+'] and reading in ['3']):
        return 6
    elif listening in ['3', '3+', '4'] and reading in ['3', '3+', '4']:
        return 4
    else:
        return 0
    
def initialize_session_state_variables(vars=SESSION_VARIABLES):
    '''helper function to initialize streamlit session state variables'''
    for var in vars:
        if var not in st.session_state:
            st.session_state[var] = None

def read_excel(file, user_id):
    '''convert lang hour excel sheet to a list'''
    df = pd.read_excel(file, engine='openpyxl')
    language_hours = []
    for _, row in df.iterrows():
        language_hour = LanguageHour(
            user_id=user_id,
            date=row['Date'],
            hours=row['Hours'],
            description=row['Description'],
            modalities=row['Modality'],
        )
        language_hours.append(language_hour)
    return language_hours

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

def create_pdf(data_fields):
    '''data_fields = {
        'Language': 'Arabic',
        'Member Name': f'TEST NAME',
        'Hours Studied': 'TESTVALUE',
        'Date': 'MAR-2023',
        'Listening': '0',
        'Reading': '0',
        'Maintenance Record': 'TEST STRING HERE',
    }'''
    reader = PdfReader('template.pdf')
    page = reader.pages[0]

    writer = PdfWriter()
    set_need_appearances_writer(writer)

    fields = reader.get_fields()
    key = pdfgen.NameObject('/V')
    value = pdfgen.create_string_object('TESTVALUE')
    fields['Member Name'][key] = value

    writer.update_page_form_field_values(page, fields=data_fields)
    writer.add_page(page)

    # Save the output PDF file to a buffer
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)

    return output_buffer

def download_database(table, engine):
    with engine.connect() as conn:
        df = pd.read_sql_table(table, conn)
        #df.to_excel(f"{table}.xlsx", engine='openpyxl', index=False)
        conn.close()
    return to_excel(df)

