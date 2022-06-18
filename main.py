import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
LHT_SHEET_ID = st.secrets["LHT_SHEET_ID"]
LST_SHEET_ID = st.secrets["LST_SHEET_ID"]
USER_SHEET = st.secrets["USER_SHEET"]
USER_SHEET_ID = st.secrets["USER_SHEET_ID"]
SERVICE_INFO = st.secrets["google_service_account"]

st.set_page_config(page_title="Language Hour Entry", page_icon="🌐", layout="centered")
credentials = service_account.Credentials.from_service_account_info(info=SERVICE_INFO, scopes=SCOPES)
service = build(serviceName="sheets", version="v4", credentials=credentials)


def write(body_data, spreadsheet_id):
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body_data).execute()

def add_row(connector, sheet_name, row) -> None:
    connector.values().append(spreadsheetId=LHT_SHEET_ID,
    range=f"{sheet_name}!A:E",
    body=dict(values=row),
    valueInputOption="USER_ENTERED",
    ).execute()

def remove_row(index, sheet_id):
    request_body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": index,
                        "endIndex": index + 1,
                    }
                }
            }
        ]
    }
    response = write(request_body)
    return response

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Sheet1")
    writer.save()
    data = output.getvalue()
    return data

def calculate_total_hours(name):
    minutes = get_data(column="Minutes", sheet_name=name)
    return sum([int(x) for x in minutes])

def calculate_required_hours(name):
    pass

def get_dataframe(connector, worksheet, sheet_name) -> pd.DataFrame:
    values = (connector.values().get(
        spreadsheetId=worksheet,
        range=f"{sheet_name}!A:E",
        ).execute()
    )
    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df[1:]
    return df

def get_data(worksheet=LST_SHEET_ID, column=None, sheet_name=USER_SHEET, range="A:E"):
    df = get_dataframe(connector=service.spreadsheets(), worksheet=worksheet, sheet_name=sheet_name, range=range)
    return df[column].tolist() if column is not None else df

def _add_member(name, username, password):
    if name in get_data(column="Name"):
        st.error("Member already exists")
        return
    add_row(connector=service.spreadsheets(), sheet_name=USER_SHEET, row=[[name, username, password]])
    req_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": name,
                    }
                }
            }
        ]
    }
    r = service.spreadsheets().batchUpdate(spreadsheetId=LHT_SHEET_ID, body=req_body).execute()
    st.success("Added member")

def request_add_member(name):
    request_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": name,
                    }
                }
            }
        ]
    }
    response = write(body_data=request_body, spreadsheet_id=LHT_SHEET_ID)

def get_sheet_id(spreadsheet_id, sheet_name):
    sheet_id = None
    for sheet in service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute():
        if sheet["properties"]["title"] == sheet_name:
            sheet_id = sheet["properties"]["sheetId"]
    return sheet_id

def remove_member(name):
    if name not in get_data("Name"):
        st.error("Member does not exist")
        return
    spreadsheet = service.spreadsheets().get(spreadsheetId=LHT_SHEET_ID).execute()
    sheet_id = None
    for sheet in spreadsheet["sheets"]:
        if sheet["properties"]["title"] == name:
            sheet_id = sheet["properties"]["sheetId"]
            print(sheet["properties"]["sheetId"])
    req_body = {
        "requests": [
            {
                "deleteSheet": {
                    "sheetId": sheet_id,
                }
            }
        ]
    }
    r = service.spreadsheets().batchUpdate(spreadsheetId=LHT_SHEET_ID, body=req_body).execute()
    user_data = get_data()
    index = user_data.index[user_data["Name"] == name].tolist()[0]
    remove_row(index)
    st.success("Removed member")

def create_tabs(names):
    for name in names:
        req_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": name,
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=LHT_SHEET_ID, body=req_body).execute()
    print("finished")

def edit_tabs(names):
    for name in names:
        if name not in ["Link", "Knights", "Template"]:
            remove_row(1, get_sheet_id(spreadsheet_id=LHT_SHEET_ID, sheet_name=name))
            #add_row(service.spreadsheets(), sheet_name=name, row=[["Date", "Minutes", "Modality", "Description", "Vocab"]])

def add_member(name):
    if name in get_data(columns="Name"):
        st.error("Member already exists")
        return
    connector = service.spreadsheets()
    add_row(connector=connector, sheet_name=name, row=[["Date", "Minutes", "Modality", "Description", "Vocab"]])

def normalize_name(name):
    # converts last, first into first last
    fullname = name.split(",")
    return fullname[1] + " " + fullname[0]
   

hashed_passwords = stauth.Hasher(get_data(worksheet=LHT_SHEET_ID, column="Password", range="A:C")).generate()
authenticator = stauth.Authenticate(get_data(worksheet=LHT_SHEET_ID, column="Name"), get_data(worksheet=LHT_SHEET_ID, column="Username"), hashed_passwords, "yummy_cookie", "key", cookie_expiry_days=30)
Name, authentication_status, username = authenticator.login("Language Hour Tracker Login", "main")


def login():
    if authentication_status:
        run()
        authenticator.logout("Logout")
    elif authentication_status == False:
        st.error('Username or password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')


def run():
    if Name == "admin":
        st.title("Admin Hub")
        expander = st.expander(label="Add Member")
        with expander:
            with st.form(key="admin_form1", clear_on_submit=True) as admin_form1:
                all_names = get_data(worksheet=LHT_SHEET_ID, column="Name", sheet_name=USER_SHEET)
                add_name = st.text_input(label="First Last", placeholder="John Smith")
                add_username = st.text_input(label="Username", placeholder="jcs")
                add_password = st.text_input(label="Password", placeholder="password123x")
                add_supervsior = st.selectbox(label="Supervisor", options=sorted(all_names))
                add_mentor = st.text_input(label="Mentor", placeholder="John Snuffy")
                submit_add_member = st.form_submit_button(label="Add Member")

            if submit_add_member:
                with st.spinner("Adding new member..."):
                    add_member(add_name, add_username, add_password)

        expander2 = st.expander(label="Remove Member")
        with expander2:
            with st.form(key="admin_form2", clear_on_submit=True) as admin_form2:
                remove_name = st.selectbox(label="by Name", options=sorted(get_data("Name")), key="name2")
                submit_remove_member = st.form_submit_button(label="Remove Member")

            if submit_remove_member:
                with st.spinner("Removing member..."):
                    remove_member(remove_name)

        with st.form(key="query_form"):
            st.text_input(label="Query member", placeholder="Enter name or username", autocomplete="")
            st.form_submit_button(label="Search")

        st.button(label="📥 Download Complete Language Hour Tracker")

    else:
        st.title("Language Hour Entry")
        with st.form(key="user_form", clear_on_submit=True) as form:
            cols = st.columns(2)
            name = cols[0].text_input(label="Name", value=normalize_name(Name), placeholder="Last name", disabled=True)
            cols = st.columns((1, 1, 1, 1))
            minutes = cols[2].number_input(label=f"Minutes - {calculate_total_hours(name)} submitted", min_value=0, max_value=60, step=15)
            date = cols[3].date_input(label="Date")
            listening = cols[0].checkbox(label="Listening")
            reading = cols[0].checkbox(label="Reading")
            speaking = cols[0].checkbox(label="Speaking")
            cols = st.columns((2, 1))
            description = cols[0].text_area(label="Description", height=150, placeholder="describe what you did\nexample:\nlistened to lvl 2+ passages about politics in Lebanon, specifically etc...\nthen answered questions about it and scored 90%. etc")
            vocab = cols[1].text_area(label="Vocab", height=150, placeholder="list the vocab you learned\nexample:\nبطيخ - watermelon\nاحتكار - monopoly\netc")
            cols = st.columns(2)
            if not name in get_data("Name"):
                st.error("Name does not exist")
                return
            uploaded_file = st.file_uploader(label="Upload your 623A")
            submitted = cols[0].form_submit_button(label="Submit")

        name = name.title()
        data = get_data()
        st.download_button(label="📥 Download myLanguageHours", data=to_excel(data), file_name="myLanguageHours.xlsx")

        expander = st.expander("Show my Language Hour entries")
        with expander:
            st.dataframe(get_data(sheet_name=name))
        
        if uploaded_file is not None:
            pass

        if submitted:
            if len(description) < 1:
                st.error("You need to include what you studied...")
                return
            if minutes <= 0:
                st.error("You need to study longer than 0 minutes...")
                return
            if not any([listening, reading, speaking]) == True:
                st.error("You need to select at least 1 modality...")
                return

            modality = ""
            if listening:
                modality += "L"
            if reading:
                modality += "R"
            if speaking:
                modality += "S"

            add_row(connector=service.spreadsheets(), sheet_name=name, row=[[str(date), minutes, modality, description, vocab]])
            st.success(f"Thanks {name}! Your entry has been submitted")
            st.balloons()


if __name__ == "__main__":
    login()
    
