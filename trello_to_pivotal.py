#encoding: utf-8
import json
import csv
import datetime
import os
import sys
import re

# It is assumed that the member names are equal in trello and pivotal tracker.

# Maps a list to state of the item.
# Cards will not be in the output if their list is not mapped.
# Use state 'unscheduled' to put in the icebox.
ALIASES = {
    'icebox':'unscheduled',  # Icebox
    'backlog':'unstarted',   # Backlog
    'started':'started',     # Current
    'finished':'finished',   # Finished
    'delivered to staging':'delivered', # Delivered
    'deployed to [demo,hq,ki]':'accepted',   # Accepted
}

STORY_TYPES = {
   '#bug':'bug',         #Bug
   '#chore':'chore',     #Chore
   '#release':'release', #Release
   '#feature':'feature', #Feature
}

# Anything that has started needs an estimate.
# The default is -1, unestimated.
ESTIMATES = {
    'started': 1,
    'finished': 1,
    'delivered': 1,
    'accepted': 1,
}

with file(sys.argv[1]) as f:
    lists = {}
    listorders = {}
    board = json.loads(f.read())
    for list in board['lists']:
        lists[list['id']] = list['name']
        listorders[list['id']] = list['pos']

members = {}
for member in board['members']:
    members[member['id']] = member['fullName']

checklists = {}
for checklist in board['checklists']:
    checklists[checklist['id']] = checklist

now = datetime.datetime.now().strftime("%Y-%m-%d+%H:%M")
from os import path
if not path.exists('trello'):
    os.mkdir('trello')

CHECK_EQUIV = {'incomplete': 'not completed',
               'complete': 'completed'}

def sluggify(string):
    return re.sub("[^a-zA-Z0-9 _-]",'', string.lower()).replace(' ', '-')

def paginate(L, num):
    return [L[i*num : (i+1)*num] for i in range((len(L)/num)+1) if L[i*num : (i+1)*num]]

def labelToState(labels):
    for label in labels:
        if label in STORY_TYPES:
            return STORY_TYPES[label]
        else:
            return 'feature'

max_num_tasks = 0
for card in board['cards']:
    if card['closed']:
        continue
    num_tasks = 0
    for checklistId in card['idChecklists']:
        checklist = checklists[checklistId]
        num_tasks += len(checklist['checkItems'])
    max_num_tasks += num_tasks
all_cards = board['cards']
all_cards.sort(key=lambda x: (-float(listorders[x['idList']]), float(x['pos'])))

for page, cards in enumerate(paginate(board['cards'], 100)):
    filename = "trello/%s_%s_%s.csv" %(sluggify(board['name']),now,page)
    with open(filename, 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',)

        writer.writerow(['Story', 'Description', 'Owned By', 'Requested By', 'Labels',
                         'Current State', 'Story Type', 'Estimate']
                        + ['Task', 'Task Status'] * max_num_tasks)
        for card in cards:
            if card['closed']:
                continue
            name = card['name'].encode("utf-8")


            list = lists[card['idList']]
            if list not in ALIASES:
              continue
            current_state = ALIASES[list]
            estimate =    ESTIMATES.get(list, -1)

            labels = [label['name'] for label in card['labels']] + ["trello","board_name"]
            if not list in ALIASES:
                labels+=[list]

            orig_description = card.get('desc', '')
            description = orig_description+'\n' if orig_description else ''
            card_members = card['idMembers']
            owner = members[card_members[0]] if card_members else ''
            checkItemStates = {item['idCheckItem']: item['state'] for item in card['checkItemStates']}

            tasks = []
            for checklistId in card['idChecklists']:
                checklist = checklists[checklistId]
                pre = checklist['name']+": " if checklist['name'] != "Checklist" else ''
                for item in checklist['checkItems']:
                    tasks += [(pre+item['name']).encode('utf-8')]
                    tasks += [CHECK_EQUIV[ checkItemStates.get(item['id'], item['state']) ]]

            row = [name,
                   (description+"Imported from %s"%card['url']).encode("utf-8"),
                   owner.encode("utf-8"),
                   owner.encode("utf-8"),
                   ','.join(labels),
                   current_state,
                   labelToState(labels),
                   estimate]+tasks
            writer.writerow(row)

