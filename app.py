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

class Kill(db.Model):
    __tablename__ = 'kill'
    id = db.Column(db.Integer, primary_key=True)
    kill_time = db.Column(db.DateTime)
    involved = db.relationship('Entity', foreign_keys='Entity.kill_id')
    victim = db.relationship('Entity', primaryjoin='Entity.id==Kill.victim_id')
    final_blow = db.relationship('Entity', primaryjoin='Entity.id==Kill.final_blow_id')
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
        self.system = Label.make_or_create(kill['solarSystemID'], '')
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
    def kills():
        return Kill.query.filter(Kill.kill == True)

    @staticmethod
    def losses():
        return Kill.query.filter(Kill.loss == True)

    @staticmethod
    def friendly():
        return Kill.query.filter(db.and_(Kill.loss == True, Kill.kill == True))

    @staticmethod
    def kills_by_day():
        by_day = defaultdict(list)
        kills = Kill.query.order_by(Kill.id.desc())
        for k in [kill.mail() for kill in kills]:
            by_day[k['kill_time'].date()].append(k)
        return sorted(by_day.items(), reverse=True)

    
    @staticmethod
    def board(chars):
        ks = Kill.kills()
        ls = Kill.losses()
        data = {'list': Kill.kills_by_day(),
                'character_count': len(chars),
                'losses': ls.count(),
                'kills': ks.count(),
                'friendlyfire': Kill.friendly().count(),
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
        self.corp = Label.make_or_create(entity['corporationID'], entity['corporationName'])
        if entity['characterName']:
            self.character = Label.make_or_create(entity['characterID'], entity['characterName'])
        else:
            self.character = self.corp

        if entity['allianceID']:
            self.alliance = Label.make_or_create(entity['allianceID'], entity['allianceName'])
        else:
            self.alliance = self.corp

        self.ship = Label.make_or_create(entity['shipTypeID'], '')

        if 'damageTaken' in entity:
            self.damage = entity['damageTaken']
        else:
            self.damage = entity['damageDone']


        

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
    def make_or_create(id, name):
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

    
class zKillAPI():
    def __init__(self):
        self.character_list = {}
        self.history = {}
        self.most_recent_killID = 0

        with open('data/characters.json', 'r') as fd:
            self.character_list = json.load(fd)
        if len(self.character_list) > 10:
            raise ValueError("More than 10 values in characters.json, zkill API only allows 10")
            # maybe later we will go full api insanity and pull two different 10 character calls

        #load current history
        try:
            with open('out/data/history.json', 'r') as fd:
                self.history = json.load(fd)
        except IOError:
            with open('out/data/history.json', 'a') as faild:
                json.dump([], faild)
            self.history = []
        if len(self.history) == 0:
            self.most_recent_killID = (14123136-1) #first killmail minus 1 to fetch all UPDATE THIS IN FUTURE KILLBOARDS
        else:
            self.most_recent_killID = self.history[-1]["killID"]
        logging.info('zKillAPI.most_recent_killID=' + str(self.most_recent_killID))

    def update_kill_history(self):
        api_call_charID_list = ','.join(str(x) for x in self.character_list.values())
        api_call_frontstr = "http://zkillboard.com/api/character/"
        api_call_backstr = "/afterKillID/"+str(self.most_recent_killID)+"/orderDirection/asc/no-items/page/"
        api_call_minus_page_num = api_call_frontstr + api_call_charID_list + api_call_backstr
        current_page = 1
        logging.info('api call: ' +api_call_minus_page_num+str(current_page)+'/')
        raw_api_data = requests.get(api_call_minus_page_num+str(current_page)+'/').json()
        raw_api_pages = raw_api_data
        while len(raw_api_data) != 0: #ensure there are no further pages
            time.sleep(10) # zkill api can be slow and tends to error out
            current_page += 1
            logging.info('api call: ' +api_call_minus_page_num+str(current_page)+'/')
            raw_api_data = requests.get(api_call_minus_page_num+str(current_page)+'/').json()
            raw_api_pages.extend(raw_api_data)
        #no more pages on the api with data
        self.history.extend(raw_api_pages)
        #for a new round of api calls, final item contains the newest killID if it exists
        self.most_recent_killID = self.history[-1]["killID"]
        logging.info('zKillAPI.most_recent_killID updated to: ' + str(self.most_recent_killID))
        return current_page

    def prune_unused_history_fields(self):
        for mail in self.history:
            mail.pop('moonID', None) #prune moon info
            mail.pop('position', None) #we don't need y,x,z in-space coords
            mail['zkb'].pop('hash', None) #prune zkill hash value
            mail['zkb'].pop('points', None) #prune points metric because it means literally nothing
            if mail.get('involved', None) == None:
                mail['involved'] = len(mail['attackers']) # save number involved because we are pruning attackers
            pruned_attackers = []
            for attacker in mail['attackers']: #keep only those on character_list or finalBlow == 1
                if attacker['finalBlow'] == 1 or attacker['characterName'] in self.character_list.keys():
                    attacker.pop('securityStatus', None) # drop sec status
                    pruned_attackers.append(attacker)
                    #save final_blow to top level location also
                    if attacker['finalBlow'] == 1:
                        mail['final_blow'] = attacker
            mail['attackers'] = pruned_attackers

    def tag_as_kill_loss_or_friendly_fire(self):
        for mail in self.history:
            #if row_type tag exists, skip this mail
            if mail.get('row_type', None) != None:
                continue
            #if one of our characters is the victim it is a loss
            if mail.get('victim', None) != None:
                if mail['victim'].get('characterName', None) in self.character_list.keys():
                    #if one of our characters is on the killmail it's not just a loss
                    #it's a friendly fire incident
                    for attacker in mail['attackers']:
                        if attacker['characterName'] in self.character_list.keys():
                            mail['row_type'] = 'row-friendlyfire'
                            break
                    if mail.get('row_type', None) == None: # if it wasn't tagged friendly fire
                        mail['row_type'] = 'row-loss'      # then it's just a loss
                else: # if one of our characters isn't teh victim then it is a kill
                    mail['row_type'] = 'row-kill'

    def tag_involved_characters(self):
        for mail in self.history:
            #if our_chracters tag exists, skip this mail
            if mail.get('our_characters', None) != None:
                continue
            #build an array of all of our characters involved
            involved = []
            for attacker in mail['attackers']:
                if attacker['characterName'] in self.character_list.keys():
                    involved.append(attacker['characterName'])
            mail['our_characters'] = involved
            mail['our_involved_html'] = ('<BR>'.join(x for x in involved))

    def kill_counts(self, killtype):
        return len([x for x in self.history if x['row_type'] == killtype])

    def engineering_number_string(self, value):
        powers = [10 ** x for x in (3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 100)]
        human_powers = ('k', 'm', 'b', 't', 'qa','qi', 'sx', 'sp', 'oct', 'non', 'dec', 'googol')
        try:
            value = int(value)
        except (TypeError, ValueError):
            return value

        if value < powers[0]:
            return str(value)
        for ordinal, power in enumerate(powers[1:], 1):
            if value < power:
                chopped = value / float(powers[ordinal - 1])
                format = ''
                if chopped < 10:
                    format = '%.2f'
                elif chopped < 100:
                    format = '%.1f'
                else:
                    format = '%i'
                return (''.join([format, human_powers[ordinal - 1]])) % chopped
        return str(value)

    def tag_formatted_values(self):
        for mail in self.history:
            #if formatted_price tag exists, skip this mail
            if mail.get('formatted_price', None) != None:
                continue
            #grab the totalValue
            mail['formatted_price'] = self.engineering_number_string(mail['zkb']['totalValue'])

    def kill_sums(self, killtype):
        r = sum(self.verify_kill(x, killtype) for x in self.history)
        return self.engineering_number_string(r)

    def verify_kill(self, k, killtype):
        if k['row_type'] in [killtype, 'row-friendlyfire']:
            if 'zkb' in k and 'totalValue' in k['zkb']:
                return k['zkb']['totalValue']
        return 0

    def kills_by_date(self):
        kills = defaultdict(list)
        for kill in reversed(self.history):
            kills[kill['killTime'].split(' ')[0]].append(kill)
        return sorted(kills.items(), key=lambda x: x[0], reverse=True)

    def use_character(self, charid):
        cs = {v:k for k,v in self.character_list.items()}
        charname = cs[charid]
        self.history = [x for x in self.history if charname in x['our_characters'] or charname == x['victim']['characterName']]

    def write_to_file(self):
        with open('out/data/history.json', 'w') as outfile:
            json.dump(self.history, outfile)

    def build(self):
        self.update_kill_history()
        self.prune_unused_history_fields()
        self.tag_as_kill_loss_or_friendly_fire()
        self.tag_involved_characters()
        self.tag_formatted_values()
        self.write_to_file()

    @property
    def data(self):
        result = {'kills':           self.kill_counts('row-kill'),
                  'losses':          self.kill_counts('row-loss'),
                  'history':         self.kills_by_date(),
                  'characters':      sorted(self.character_list.items()),
                  'money_lost':      self.kill_sums('row-loss'),
                  'money_killed':    self.kill_sums('row-kill'),
                  'friendlyfire':    self.kill_counts('row-friendlyfire'),
                  'character_count': len(self.character_list)}
        return result

@app.route('/', defaults={'charid': None})
@app.route('/<int:charid>/')
def index(charid):
    killboard = Kill.board(app.config['characters'])
    return render_template('index.html', **killboard)

@freezer.register_generator
def index():
    zKill = zKillAPI()
    for x in zKill.character_list.values():
        yield {'charid': x}
    yield {'charid': None}


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

