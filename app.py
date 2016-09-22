import sys
import json
import logging
import requests
import time
from datetime import datetime
from collections import defaultdict

import yaml
from flask import Flask, render_template
from flask_frozen import Freezer
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

with open('config.yml') as fd:
    app.config.update(yaml.load(fd))

freezer = Freezer(app)
db = SQLAlchemy(app)

@app.template_filter()
def humanize(n):
    # modified from https://github.com/jmoiron/humanize
    powers = [10 ** x for x in (3, 6, 9, 12, 15, 18)]
    words = ('k', 'm', 'b', 't', 'qa', 'qi')

    try:
        n = float(n)
        n = int(n)
    except(ValueError, TypeError):
        return str(n)

    if n < powers[0]:
        return str(n)

    for ordinal, power in enumerate(powers[1:], 1):
        if n < power:
            chopped = n / float(powers[ordinal - 1])
            return '{:.1f}{}'.format(chopped, words[ordinal - 1])
    return str(n)


kill_association = db.Table('association', db.metadata,
                  db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                  db.Column('kill_id', db.Integer, db.ForeignKey('kill.id')))

label_association = db.Table('association', db.metadata,
                   db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                   db.Column('label_id', db.Integer, db.ForeignKey('label.id')),
                   extend_existing=True)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    kills = db.relationship("Kill", secondary=kill_association)
    characters = db.relationship("Label", secondary=label_association)

class Kill(db.Model):
    __tablename__ = 'kill'
    id = db.Column(db.Integer, primary_key=True)
    kill_time = db.Column(db.DateTime)
    involved = db.relationship('Entity', foreign_keys='Entity.kill_id', backref='involved_kill')
    victim = db.relationship('Entity', primaryjoin='Entity.id==Kill.victim_id', backref='victim_kill')
    final_blow = db.relationship('Entity', primaryjoin='Entity.id==Kill.final_blow_id', backref='final_blow_kill')
    system = db.relationship('Label', primaryjoin='Label.id==Kill.system_id')
    others = db.Column(db.Integer)
    value = db.Column(db.Float)
    kill = db.Column(db.Boolean, default=True)
    loss = db.Column(db.Boolean, default=False)

    
    victim_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    system_id = db.Column(db.Integer, db.ForeignKey('label.id'))
    final_blow_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    
    url = 'https://zkillboard.com/api{}'
    kills_slug = '/character/{chars}/{killid}no-items/page/{page}'

    def __init__(self, kill):
        self.id = kill['killID']
        self.kill_time = datetime.strptime(kill['killTime'], '%Y-%m-%d %H:%M:%S')
        self.victim = Entity(kill['victim'])
        self.system = Label.get_or_create(kill['solarSystemID'], '')
        self.final_blow = Entity(list(filter(lambda x: x['finalBlow'], kill['attackers']))[0])
        self.value = kill['zkb']['totalValue']
        self.others = len(kill['attackers'])
        for inv in kill['attackers']:
            if inv['characterName'] in app.config['characters']:
                self.involved.append(Entity(inv))

        if self.victim.character.name in app.config['characters']:
            self.loss = True
        if not self.involved:
            self.kill = False
    
    def mail(self):
        data = {'killid': self.id,
                'value': self.value,
                'others': self.others,
                'system': self.system,
                'victim': self.victim,
                'kill_time': self.kill_time,
                'mail_type': self.mail_type(),
                'final_blow': self.final_blow,
                'involved': sorted(self.involved, key=lambda x: x.damage)}
        return data

    def mail_type(self):
        if self.loss and self.kill:
            return 'friendlyfire'
        if self.loss:
            return 'loss'
        if self.kill:
            return 'kill'

    @staticmethod
    def kills_by_day(kills):
        by_day = defaultdict(list)
        for k in [kill.mail() for kill in kills]:
            by_day[k['kill_time'].date()].append(k)
        return sorted(by_day.items(), reverse=True)
    
    @staticmethod
    def filter_kills(kills, kill_type):
        return list(filter(lambda x: x.mail_type() == kill_type, kills))

    @staticmethod
    def board(chars, characterid = None):
        if characterid and characterid in chars.values():
            entities = Entity.query.filter(Entity.character_id == characterid).order_by(Entity.id.desc())
            kills = [e.kill for e in entities]
        else:
            kills = Kill.query.order_by(Kill.id.desc())

        ks = Kill.filter_kills(kills, 'kill')
        ls = Kill.filter_kills(kills, 'loss')
        data = {'list': Kill.kills_by_day(kills),
                'character_count': len(chars),
                'losses': len(ls),
                'kills': len(ks),
                'friendlyfire': len(Kill.filter_kills(kills, 'friendlyfire')),
                'isk_killed': sum(x.value for x in ks),
                'isk_lost': sum(x.value for x in ls),
                'characters': sorted(chars.items(), key=lambda x: x[0])}
        return data

    @staticmethod
    def makeurl(chars, page):
        chars, lastkill = ','.join(str(x) for x in chars), ''
        result = Kill.query.order_by(Kill.id.desc()).first()
        if result:
            lastkill = result.id

        slugs = {'chars': chars, 'killid': lastkill, 'page': page}

        return Kill.url.format(Kill.kills_slug.format(**slugs))

    @staticmethod
    def pull(chars, page=1):
        kills = []
        while page:
            print('pulling page {} ... '.format(page))
            result = requests.get(Kill.makeurl(chars, page))
            results = result.json()
            print('{} results'.format(len(results)))

            if not results:
                break
            
            kills += results

            if len(results) is 200:
                page += 1
            else:
                page = None

        if kills:
            for k in kills:
                db.session.add(Kill(k))
            db.session.commit()
        
            Label.populate()

    def __repr__(self):
        return '<Kill {}: {}>'.format(self.id, self.victim.character.name)


class Entity(db.Model):
    __tablename__ = 'entity'
    id = db.Column(db.Integer, primary_key=True)
    kill_id = db.Column(db.Integer, db.ForeignKey('kill.id'))
    character = db.relationship('Label', primaryjoin='Label.id==Entity.character_id' )
    corp = db.relationship('Label', primaryjoin='Label.id==Entity.corp_id')
    alliance = db.relationship('Label', primaryjoin='Label.id==Entity.alliance_id')
    ship = db.relationship('Label', primaryjoin='Label.id==Entity.ship_id')
    damage = db.Column(db.Integer)

    character_id = db.Column(db.Integer, db.ForeignKey('label.id'))
    corp_id = db.Column(db.Integer, db.ForeignKey('label.id'))
    alliance_id = db.Column(db.Integer, db.ForeignKey('label.id'))
    ship_id = db.Column(db.Integer, db.ForeignKey('label.id'))
    
    def __init__(self, entity): 
        self.corp = Label.get_or_create(entity['corporationID'], entity['corporationName'])
        if entity['characterName']:
            self.character = Label.get_or_create(entity['characterID'], entity['characterName'])
        else:
            self.character = self.corp

        if entity['allianceID']:
            self.alliance = Label.get_or_create(entity['allianceID'], entity['allianceName'])
        else:
            self.alliance = self.corp

        self.ship = Label.get_or_create(entity['shipTypeID'], '')

        if 'damageTaken' in entity:
            self.damage = entity['damageTaken']
        else:
            self.damage = entity['damageDone']


    @property
    def kill(self):
        r = getattr(self, 'involved_kill') or getattr(self, 'victim_kill') or getattr(self, 'final_blow_kill')
        if isinstance(r, list):
            r = r[0]
        return r

    def __repr__(self):
        return '<Entity: {}>'.format(self.character.name)


class Label(db.Model):
    __tablename__ = 'label'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    def __init__(self, id, name):
        self.id = id
        self.name = name

    @staticmethod
    def get_or_create(id, name):
        q = Label.query.get(id)
        if not q:
            q = Label(id, name)
            db.session.add(q)
            db.session.commit()

        return q

    @staticmethod
    def unnamed_systems():
        return Label.query.filter(Label.id >= 30000000).filter(Label.name == '')

    @staticmethod
    def unnamed_types():
        return Label.query.filter(Label.id < 30000000).filter(Label.name == '')

    @staticmethod
    def populate():
        systems = Label.unnamed_systems()
        for system in systems:
            r = requests.get('https://crest-tq.eveonline.com/solarsystems/{}/'.format(system.id))
            system.name = r.json()['name']

        types = Label.unnamed_types()
        with open('typeids.json') as fd:
            sdd = json.load(fd)
        for t in types:
            t.name = sdd[str(t.id)]

        db.session.commit()

    def __repr__(self):
        return '<Label: {}>'.format(self.name)


@app.route('/', defaults={'charid': None})
@app.route('/<int:charid>/')
def index(charid):
    killboard = Kill.board(app.config['characters'], charid)
    return render_template('index.html', **killboard)

@freezer.register_generator
def index():
    yield {'charid': None}
    for c in app.config['characters'].values():
        yield {'charid': c }


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == 'debug':
        logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1 and sys.argv[1] == 'build':
        freezer.freeze()

    elif len(sys.argv) > 1 and sys.argv[1] == 'forcezkill':
        #keep going until first page is empty
        zKill = zKillAPI()
        while zKill.update_kill_history() != 1:
            time.sleep(10)
        zKill.prune_unused_history_fields()
        zKill.tag_as_kill_loss_or_friendly_fire()
        zKill.tag_involved_characters()
        zKill.tag_formatted_values()
        zKill.write_to_file()
    else:
        app.run(debug=True, host='0.0.0.0')

