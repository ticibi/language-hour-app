import streamlit as st

def card(title, text):
    # Style the card
    st.markdown(
        """
        <style>
        .card {
            padding: 1rem;
            margin-bottom: 5px;
            background-color: rgb(14, 17, 23);
            box-shadow: 0 3px 4px rgba(0, 0, 0, 1);
            border-radius: 0.25rem;
            border: 1px solid rgba(0, 0, 0, 0.125);
        }
        .card:hover {
            background-color: rgb(25, 30, 35);
            cursor: pointer;
        }
        .card-header {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }
        .card-body {
            font-size: 1rem;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        </style>
        """
        ,
        unsafe_allow_html=True
    )
    # Html the card
    st.markdown(
        f"""
        <div class="card">
            <div class="card-body">{title}
            <div class="card-body">{text}</div>
        </div>
        """
        ,
        unsafe_allow_html=True
    )



