from models import MODELS, TABLE
from db import session
from utils import dot_dict


def load_user_models(db, user_id) -> dict:
    user_data = {}
    for model_name in MODELS:
        if model_name in ['User', 'Group']:
            continue
        model = TABLE[model_name]
        with session(db) as db:
            if model_name == 'Message':
                data = db.query(model).filter_by(recipient_id=user_id).all()
            else:
                data = db.query(model).filter_by(user_id=user_id).all()
            data_list = []
            for item in data:
                item_dict = item.__dict__.copy()
                item_dict.pop('_sa_instance_state', None)
                data_list.append(dot_dict(item_dict))
            user_data[model_name] = data_list
    return dot_dict(user_data)

