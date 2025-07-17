import json

def get_user_settings(user_id):
    try:
        with open('user_settings.json', 'r') as f:
            data = json.load(f)
        return data.get(str(user_id), {})
    except FileNotFoundError:
        return {}

def set_user_settings(user_id, settings):
    data = {}
    try:
        with open('user_settings.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass
    data[str(user_id)] = settings
    with open('user_settings.json', 'w') as f:
        json.dump(data, f)
