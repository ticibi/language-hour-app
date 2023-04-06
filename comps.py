import streamlit as st
from streamlit_option_menu import option_menu

@st.cache_data
def add_boostrap():
    html = '''
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    '''
    return st.markdown(html, unsafe_allow_html=True)

def login():
    return f'''
    <form class="row g-3" method="POST">
        <div class="col-md-12">
            <label for="username" class="form-label">Username</label>
            <input type="text" name="username" class="form-control" id="username">
        </div>
        <div class="col-md-12">
          <label for="password" class="form-label">Password</label>
          <input type="password" name="password" class="form-control" id="password">
        </div>
        <div class="col-12">
            <button type="submit" class="btn btn-primary" value="Login">Login</button>
          </div>
      </form>
      '''

def navbar(options):
    selected = option_menu(
        menu_title='Langauge Training Management',
        options=options,
        orientation='horizontal',
        icons=['app', 'app', 'app', 'app'],
        menu_icon='diamond',

    )
    return selected

def form(title, user):
    return f'''
    <form>
        <h4>{title}</h4>
        <div class="row">
            <div class="col">
                <div class="form-outline">
                    <label class="form-label" for="name">Name</label>
                    <input disabled type="text" id="name" class="form-control" value="{user.name}" />
                </div>
            </div>
            <div class="col">
                <div class="form-outline">
                    <label class="form-label" for="date">Date</label>
                    <input required type="date" name="date" id="date" class="form-control" />
                </div>
            </div>
            <div class="col">
                <div class="form-outline">
                    <label class="form-label" for="hours">Hours</label>
                    <input required type="number" name="hours" id="hours" class="form-control" />
                </div>
            </div>
            <div class="form-outline mb-4">
                <div class="btn-group" role="group" id="activities">
                    <label for="activities">Select Activities</label>
                </div>
            </div>
        <div class="form-outline mb-4">
            <label class="form-label" for="description">Description</label>
            <textarea required class="form-control" name="description" id="description" rows="4"></textarea>
        </div>
        <button type="submit" value="Submit" class="btn btn-primary btn-block mb-4">Submit</button>
      </form>
    '''

def card():
    return ''''''

