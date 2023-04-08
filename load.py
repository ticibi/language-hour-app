from models import MODELS, TABLE
from db import session


def get_user_models(db, user_id) -> dict:
    user_data = {}
    for model_name in MODELS:
        if model_name in ['User', 'Group', 'Message']:
            continue
        model = TABLE[model_name]
        with session(db) as db:
            data = db.query(model).filter_by(user_id=user_id).all()
        if data:
            user_data[model_name] = data
    return user_data
