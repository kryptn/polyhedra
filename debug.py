from app import app, db, Kill, Label, Entity
import json, requests

def get_test_data():
    r = requests.get('https://zkillboard.com/api/kills/charactokerID/268946627/no-items/').json()
    with open('test_data.json', 'w') as fd:
        json.dump(r, fd)

with open('test_data.json') as fd:
    data = json.load(fd)

c = app.config['characters'].values()

def reset():
    db.create_all()
    for x in data:
        db.session.add(Kill(x))

