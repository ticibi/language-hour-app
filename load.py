import streamlit as st
from models import MODELS, TABLE
from db import session
from utils import dot_dict

@st.cache_data
def load_user_models(_db, user_id) -> dict:
    user_data = {}
    data = None
    data2 = None

    for model_name in MODELS:
        # User model has already been loaded into st.session_state
        # Group model is not needed on the clients side
        if model_name in ['User', 'Group']:
            continue

        # Log model is only needed for admin users
        if model_name in ['Log']:
            if not st.session_state.current_user.is_admin:
                continue
        model = TABLE[model_name]

        with session(_db) as _db:
            # Message model does not contain a user_id field
            if model_name == 'Message':
                data = _db.query(model).filter_by(recipient_id=user_id).all()
                data2 = _db.query(model).filter_by(sender_id=user_id).all()
            else:
                data = _db.query(model).filter_by(user_id=user_id).all()
            data_list = []
            data2_list = []

            # Populating the data into a dot dict
            for item in data:
                item_dict = item.__dict__.copy()
                item_dict.pop('_sa_instance_state', None)
                data_list.append(dot_dict(item_dict))
            
            if data2 is not None:
                for item in data2:
                    item_dict = item.__dict__.copy()
                    item_dict.pop('_sa_instance_state', None)
                    data2_list.append(dot_dict(item_dict))

            if data2 is not None:
                user_data[model_name] = data_list + data2_list
            else:
                user_data[model_name] = data_list
    return dot_dict(user_data)

