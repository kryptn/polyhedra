from app import app, db, Kill, Party, Entity
import json, requests

def get_test_data():
    r = requests.get('https://zkillboard.com/api/kills/charactokerID/268946627/no-items/').json()
    with open('test_data.json', 'w') as fd:
        json.dump(r, fd)

with open('test_data.json') as fd:
    data = json.load(fd)
c = app.config['characters'].values()
