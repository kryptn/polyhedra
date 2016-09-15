import sys
import json
import logging
import requests
import time
from datetime import datetime

from flask import Flask, render_template
from flask_frozen import Freezer


app = Flask(__name__)
freezer = Freezer(app)
app.config['FREEZER_DESTINATION'] = 'out/build'
app.config['FREEZER_RELATIVE_URLS'] = True

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

    def write_to_file(self):
        with open('out/data/history.json', 'w') as outfile:
            json.dump(self.history, outfile)

@app.route('/')
def index():
    zKill = zKillAPI()
    zKill.update_kill_history()
    zKill.prune_unused_history_fields()
    zKill.tag_as_kill_loss_or_friendly_fire()
    zKill.tag_involved_characters()
    zKill.write_to_file()
    shorthand = datetime.now().strftime("%Y-%d-%m")
    longhand = datetime.now().strftime("%B %d, %Y")
    return render_template('index.html', shorthand=shorthand, longhand=longhand, killmails=reversed(zKill.history))

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
        zKill.write_to_file()
    else:
        app.run(debug=True, host='0.0.0.0')

