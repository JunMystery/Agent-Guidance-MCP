import pickle

def load_user_data(data):
    return pickle.loads(data)

user = load_user_data(request.body)
