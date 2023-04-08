from models import MODELS, TABLE


def get_user_models(db, user_id) -> dict:
    user_data = {}
    for model_name in MODELS:
        if model_name in ['User', 'Group', 'Message']:
            continue
        model = TABLE[model_name]
        data = db.query(model).filter_by(user_id=user_id).all()
        if data:
            user_data[model_name] = data
    db.close()
    return user_data
