import os
import selenium as sl
import random
from selenium.webdriver.common.by import By
import pprint
import json

pp = pprint.PrettyPrinter(depth=4)

playerListFile = '../players'
roomListFile = '../roomNames'
stateFile = '../state'
loginFile = '../loginDetails'


def WriteState(state):
	with open(stateFile + '.json', 'w') as outfile:
		json.dump(state, outfile, indent=4)


def ReadState():
	with open(stateFile + '.json', 'r') as f:
		return json.load(f)


def LoadFileToList(fileName):
	with open('{}.txt'.format(fileName)) as file:
	    lines = [line.rstrip() for line in file]
	return lines


def ListRemove(myList, element):
	if element not in myList:
		return myList
	myList = myList.copy()
	myList.remove(element)
	return myList


def DictRemove(myDict, element):
	if element not in myDict:
		return myDict
	myDict = myDict.copy()
	myDict.pop(element)
	return myDict


def GetListInput(question, choices):
	for i, choice in enumerate(choices):
		question = question + ' [{}] {},'.format(i + 1, choice)
	question = question[:-1] + ': '
	
	validResponses = [str(i + 1) for i in range(len(choices))]
	response = input(question)
	while response not in (validResponses + choices):
		response = input(question)
	if response in choices:
		return response
	return choices[int(response) - 1]


def InitialiseWebDriver():
	loginDetails = LoadFileToList(loginFile)
	# Using Chrome to access web
	driver = sl.webdriver.Chrome()# Open the website
	
	driver.get('https://zero-k.info')
	driver.implicitly_wait(0.5)
	
	nameBox = driver.find_element(By.NAME, 'login')
	nameBox.send_keys(loginDetails[0])
	
	
	nameBox = driver.find_element(By.NAME, 'password')
	nameBox.send_keys(loginDetails[1])
	
	login_button = driver.find_element(By.NAME,'zklogin')
	login_button.click()
	
	driver.get('https://zero-k.info/Tourney')
	driver.implicitly_wait(0.5)
	return driver


def InitializeState(players, roomNames):
	if os.path.isfile(stateFile + '.json'):
		state = ReadState()
		return state
	state = {
		'queue' : players,
		'maxQueueLength' : 2,
		'playerRoomPreference' : {},
		'rooms' : {name : {
			'name' : name,
			'index' : 0,
			'finished' : True,
		} for name in roomNames},
	}
	WriteState(state)
	return state


def PrintState(state):
	runningRooms = [data for name, data in state['rooms'].items() if not data['finished']]
	for room in runningRooms:
		print('Running: "{}": {} vs {}'.format(
			room['createdName'], room['players'][0], room['players'][1]))
	print('Queue: {}'.format(state['queue']))


def FindRoomForPlayers(state, players):
	checkRooms = []
	for name in players:
		if name in state['playerRoomPreference']:
			checkRooms.append(state['playerRoomPreference'][name])
	checkRooms = checkRooms + list(state['rooms'].keys())
	
	for room in checkRooms:
		if state['rooms'][room]['finished']:
			state['rooms'][room]['finished'] = False
			return state['rooms'][room]
	return False


def MakeRooms(driver, roomsToMake):
	roomStr = ''
	first = True
	for name, data in roomsToMake.items():
		if first:
			first = False
		else:
			roomStr = roomStr + '//'
		roomStr = roomStr + '{},{},{}'.format(name, data[0], data[1])
	massRoomField = driver.find_element(By.NAME,'battleList')
	massRoomField.clear()
	massRoomField.send_keys(roomStr)
	
	createBattles = driver.find_element(
		By.XPATH,
		'//input[@type="submit" and @value="Create Battles" and contains(@class, "js_confirm")]')
	createBattles.click()


def SetupRequiredRooms(driver, state):
	rooms = {}
	while len(state['queue']) > state['maxQueueLength']:
		room = FindRoomForPlayers(state, state['queue'][:2])
		room['index'] = room['index'] + 1
		room['players'] = state['queue'][:2]
		room['createdName'] = 'FC {} {}'.format(room['name'], room['index'])
		rooms[room['createdName']] = state['queue'][:2]
		state['queue'] = state['queue'][2:]
		print('Adding room "{}": {} vs {}'.format(
			room['createdName'], room['players'][0], room['players'][1]))
	
	if len(rooms) > 0:
		MakeRooms(driver, rooms)
	return state


def HandleRoomFinish(state, room):
	if room not in state['rooms']:
		return state
	roomData = state['rooms'][room]
	if roomData['finished']:
		return state
	winner = GetListInput('Who won?', roomData['players'])
	loser  = ListRemove(roomData['players'], winner)[0]
	
	roomData['finished'] = True
	state['queue'] = [winner] + state['queue'] + [loser]
	state['playerRoomPreference'][winner] = room
	state['playerRoomPreference'] = DictRemove(state['playerRoomPreference'], loser)
	return state


players = LoadFileToList(playerListFile)
roomNames = LoadFileToList(roomListFile)
random.shuffle(players)
print('Initial players', players)
print('roomNames', roomNames)

state  = InitializeState(players, roomNames)
driver = InitialiseWebDriver()

while True:
	state = SetupRequiredRooms(driver, state)
	print('====================================')
	PrintState(state)
	
	WriteState(state)
	runningRooms = [name for name, data in state['rooms'].items() if not data['finished']]
	response = GetListInput('Which room finished?', runningRooms)
	state = ReadState()
	
	state = HandleRoomFinish(state, response)
	print('Queue: {}'.format(state['queue']))
