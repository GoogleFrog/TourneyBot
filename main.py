import os
import selenium as sl
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
import pprint
import json

import time
import threading
import logging

import tkinter as tk

pp = pprint.PrettyPrinter(depth=4)

playerListFile = '../players'
roomListFile = '../roomNames'
stateFile = '../state_test'
loginFile = '../loginDetails'
prefix = 'FC '
channelName = 'fc'

pauseMain = True
killMain  = False
statusString = False
addRemoveString = False
playersToAdd = []
playersToRemove = []
playersToRemoveQueueOnly = []
wantSuddenDeath = False
forceUpdate = 0

WANT_FILL = 'empty.'
MAX_JOIN_ATTEMPT = 4

state = {}

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

def Opt(table, parameter, default=False):
	if parameter in table:
		return table[parameter]
	return default


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


def ProcessTableRow(row):
	elementList = row.find_elements(By.XPATH, ".//*")
	elements = {e.text : e for e in elementList}
	elementNames = list(elements.keys())
	rowData = {}
	if 'Force join' in elements:
		rowData['forceJoin'] = elements['Force join']
	if 'Delete' in elements:
		rowData['delete'] = elements['Delete']
	
	rowData['playersHaveJoined'] = (elementNames[0].count('  IN') > 1)
		
	if elementNames[4] == '  IN':
		rowData['players'] = [elementNames[3], elementNames[5]]
	else:
		rowData['players'] = [elementNames[3], elementNames[4]]
	
	selectNext = False
	for name, element in elements.items():
		if selectNext and element.text.count(' ') == 0:
			rowData['battleID'] = element.text[1:]
			break
		if name.count(' 2 on ') > 0:
			selectNext = True
	return elementNames[1], rowData


def GetRoomTable(driver):
	tables = driver.find_elements(By.TAG_NAME, 'table')
	elements = False
	for table in tables:
		if table.text.count('Force join') > 0:
			elements = table.find_elements(By.XPATH, ".//*")
			break
	if elements is False:
		return False

	rows = {}
	for e in elements:
		if e.text.count(prefix) == 1 and e.text.count('Force join') == 1:
			name, rowData = ProcessTableRow(e)
			rows[name] = rowData
	return rows


def InitializeState():
	if os.path.isfile(stateFile + '.json'):
		state = ReadState()
		return state
	players = LoadFileToList(playerListFile)
	roomNames = LoadFileToList(roomListFile)
	random.shuffle(players)
	
	state = {
		'queue' : players,
		'maxQueueLength' : 1,
		'maxQueueLengthTimer' : False,
		'nextMaxQueueLength' : 1,
		"postReadTimer"  : 5,
		"postSetupTimer" : 8,
		'stateUpdated' : True,
		'lobbyChannel' : channelName,
		'playerRoomPreference' : {},
		'winStreak' : {},
		'toDelete' : [],
		'rooms' : {name : {
			'name' : name,
			'index' : 0,
			'finished' : True,
		} for name in roomNames},
		'completedGames' : {},
	}
	WriteState(state)
	return state


def UpdateUiStatus(state):
	global statusString
	runningRooms = [data for name, data in state['rooms'].items() if not data['finished']]
	status = 'Queue: {}'.format(state['queue'])
	for room in runningRooms:
		roomSummary = '{}: {} vs {}'.format(
			room['createdName'], room['players'][0], room['players'][1])
		status = status + '\n' + roomSummary
	statusString.set(status)


def PrintState(state):
	runningRooms = [data for name, data in state['rooms'].items() if not data['finished']]
	status = 'Queue: {}'.format(state['queue'])
	print(status)
	for room in runningRooms:
		roomSummary = '{}: {} vs {}'.format(
			room['createdName'], room['players'][0], room['players'][1])
		print('Running: ' + roomSummary)


def UpdateAddRemoveString():
	global addRemoveString
	newStr = ''
	if len(playersToAdd) > 0:
		newStr = newStr + 'Adding: ' + str(playersToAdd) + '\n'
	if len(playersToRemove) > 0:
		newStr = newStr + 'Force Remove: ' + str(playersToRemove) + '\n'
	if len(playersToRemoveQueueOnly) > 0:
		newStr = newStr + 'Queue Remove: ' + str(playersToRemoveQueueOnly) + '\n'
	addRemoveString.set(newStr)


def PrintBattles():
	if state is False:
		return
	print('Battle Links')
	print('{} games:'.format(len(list(state['completedGames'].keys()))))
	print('[spoiler]')
	for name in list(state['completedGames'].keys()):
		print(name)
	print('[/spoiler]')
	print('')
	print('Room champions:')
	
	# Print King of the X win stats
	for series in state['rooms'].keys():
		wins = {}
		totalGames = 0
		for battleID, game in state['completedGames'].items():
			if game['series'] == series:
				wins[game['winner']] = Opt(wins, game['winner'], 0) + 1
				totalGames = totalGames + 1
		wins = sorted(wins.items(), key=lambda x : x[1], reverse=True)
		if len(wins) > 0:
			winners = [x[0] for x in wins if wins[0][1] == x[1]]
			winnerStr = ' and '.join(['@{}'.format(w) for w in winners])
			print(' * King of the {}: {} ({} wins out of {} games overall)'.format(series, winnerStr, wins[0][1], totalGames)) 
		
	print('')
	print('Player scores:')
	# Print game stats
	playerWins = {}
	playerLosses = {}
	for battleID, game in state['completedGames'].items():
		playerWins[game['winner']] = Opt(playerWins, game['winner'], 0) + 1
		playerLosses[game['loser']] = Opt(playerLosses, game['loser'], 0) + 1
	players = list(set(list(playerWins.keys()) + list(playerLosses.keys())))
	players = sorted(players, key=lambda x : (
		Opt(playerWins, x, 0) + 0.001*Opt(playerLosses, x, 0)),
		reverse=True)
	for playerName in players:
		print(' * @{}: {} wins, {} games'.format(
			playerName,
			Opt(playerWins, playerName, 0),
			Opt(playerWins, playerName, 0) + Opt(playerLosses, playerName, 0))
		)
	
	# Print matchups.
	match = {}
	for battleID, game in state['completedGames'].items():
		players = [game['winner'], game['loser']]
		players = '.'.join(sorted(players))
		if players not in match:
			match[players] = {game['winner'] : 0, game['loser'] : 0}
		match[players][game['winner']] += 1
	matchOrder = sorted(list(match.keys()),  key=lambda x : (
		list(match[x].values())[0] + list(match[x].values())[1]),
		reverse=True
	)
	for matchup in matchOrder:
		print(match[matchup])
			

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


def ReplaceWantFill(state, player):
	fillIndex = [i for i, x in enumerate(state['queue']) if x == WANT_FILL][0]
	state['queue'][fillIndex] = player
	state['stateUpdated'] = True
	return state


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
	
	alert = Alert(driver)
	alert.accept()
	
	joinAttempts = {}
	tryForceJoin = True
	while tryForceJoin:
		driver.implicitly_wait(0.5)
		tryForceJoin = False
		rows = GetRoomTable(driver)
		for name, rowData in rows.items():
			if name in roomsToMake:
				if name not in joinAttempts:
					joinAttempts[name] = 0
				if 'forceJoin' in rowData and not rowData['playersHaveJoined'] and joinAttempts[name] < MAX_JOIN_ATTEMPT:
					print('Force joining ' + name)
					rowData['forceJoin'].click()
					joinAttempts[name] = joinAttempts[name] + 1
					driver.implicitly_wait(0.5 * joinAttempts[name])
					tryForceJoin = True
					break
	return {n : (v < 4) for n, v in joinAttempts.items()}


def CheckJoinRooms(driver):
	# Update a single room join just in case.
	rows = GetRoomTable(driver)
	for name, rowData in rows.items():
		if (not rowData['playersHaveJoined']) and 'battleID' not in rowData:
			rowData['forceJoin'].click()
			driver.implicitly_wait(0.5)
			return
	return


def SetupRequiredRooms(driver, state):
	rooms = {}
	while (len(state['queue']) > state['maxQueueLength']) and (WANT_FILL not in state['queue'][:2]):
		room = FindRoomForPlayers(state, state['queue'][:2])
		room['index'] = room['index'] + 1
		room['players'] = state['queue'][:2]
		room['createdName'] = '{}{} {}'.format(prefix, room['name'], room['index'])
		rooms[room['createdName']] = state['queue'][:2]
		state['queue'] = state['queue'][2:]
		print('Adding room "{}": {} vs {}'.format(
			room['createdName'], room['players'][0], room['players'][1]))
	
	if len(rooms) > 0:
		state['stateUpdated'] = True
		if state['maxQueueLengthTimer'] is not False:
			state['maxQueueLengthTimer'] = state['maxQueueLengthTimer'] - 1
			if state['maxQueueLengthTimer'] <= 0:
				state['maxQueueLength'] = state['nextMaxQueueLength']
				state['maxQueueLengthTimer'] = False
		success = MakeRooms(driver, rooms)
	else:
		CheckJoinRooms(driver)
	return state


def CleanUpRooms(driver, state):
	if len(state['toDelete']) == 0:
		return state
	
	for roomName in state['toDelete']:
		pageRooms = GetRoomTable(driver)
		print('Trying to delete', roomName)
		if (pageRooms is not False) and (roomName in pageRooms) and ('delete' in pageRooms[roomName]):
			print('Deleting', roomName)
			pageRooms[roomName]['delete'].click()
			alert = Alert(driver)
			alert.accept()
			driver.implicitly_wait(0.5)
			state['toDelete'].remove(roomName)
	return state


def HandleRoomFinish(state, room, battleID, winner=False):
	if room not in state['rooms']:
		return state
	roomData = state['rooms'][room]
	if roomData['finished']:
		return state
	
	if winner is False:
		winner = GetListInput('Who won?', roomData['players'])
	loser     = ListRemove(roomData['players'], winner)[0]
	forumLink = '@B{}'.format(battleID)
	
	roomData['finished'] = True
	state['toDelete'].append(roomData['createdName'])
	if len(state['queue']) == 0:
		state['queue'] = [winner, WANT_FILL, loser]
	elif WANT_FILL in state['queue']:
		state = ReplaceWantFill(state, winner)
		state['queue'] = state['queue'] + [loser]
	else:
		state['queue'] = [winner] + state['queue'] + [loser]
	state['playerRoomPreference'][winner] = room
	state['playerRoomPreference'] = DictRemove(state['playerRoomPreference'], loser)
	state['completedGames'][forumLink] = {
		'series' : room,
		'name'   : roomData['createdName'],
		'winner' : winner,
		'loser'  : loser,
	}
	state['stateUpdated'] = True
	return state


def GetBattleWinner(driver, battleID):
	print('Checking battle "{}"'.format(battleID))
	driver.get('https://zero-k.info/Battles/Detail/{}?ShowWinners=True'.format(battleID))
	driver.implicitly_wait(0.5)
	
	winnerBox = driver.find_element(By.CLASS_NAME, 'fleft.battle_winner')
	elements = winnerBox.find_elements(By.XPATH, ".//*")
	userNameBox = winnerBox.find_element(By.CSS_SELECTOR, "a[href^='/Users/Detail/']")
	return userNameBox.text
	

def UpdateChat(driver, state):
	if state['lobbyChannel'] is False:
		return state, False
	
	driver.get('https://zero-k.info/Lobby/Chat?Channel={}'.format(state['lobbyChannel']))
	driver.implicitly_wait(0.5)
	time.sleep(1.6)
	
	tables = driver.find_elements(By.XPATH, ".//*")
	textList = [x.text for x in tables]
	chatList = False
	for text in textList:
		if 'ago' in text and '\n' in text:
			split = text.split('\n')
			if (
					len(split) > 1 and 
					split[0] == '#{}'.format(state['lobbyChannel']) and
					split[1] == 'Time User Text'):
				chatList = split[2:]
	if chatList is False:
		return state, True
	
	chatList = CleanAgo(chatList)
	print(chatList)
	
	return state, True


def UpdateGameState(driver, state):
	driver.get('https://zero-k.info/Tourney') # Refresh page
	driver.implicitly_wait(0.5)

	pageRooms = GetRoomTable(driver)
	needReturnToPage = False
	if pageRooms is False:
		return state
	
	for baseName, roomData in state['rooms'].items():
		if 'createdName' in roomData and roomData['createdName'] in pageRooms:
			pageData = pageRooms[roomData['createdName']]
			if 'battleID' in pageData and (not roomData['finished']):
				winner = GetBattleWinner(driver, pageData['battleID'])
				state = HandleRoomFinish(state, baseName, pageData['battleID'], winner=winner)
				needReturnToPage = True
	
	state, needReturnToPage = UpdateChat(driver, state)
	
	if needReturnToPage:
		driver.get('https://zero-k.info/Tourney')
		driver.implicitly_wait(0.5)
	return state


def RemovePlayerFromState(state, player):
	if player in state['queue']:
		state['queue'] = ListRemove(state['queue'], player)
		state['stateUpdated'] = True
		return state
	for name, roomData in state['rooms'].items():
		if (not roomData['finished']) and (player in roomData['players']):
			roomData['finished'] = True
			state['toDelete'].append(roomData['createdName'])
			otherPlayer = ListRemove(roomData['players'], player)[0]
			state['queue'] = [otherPlayer] + state['queue']
			state['stateUpdated'] = True
			return state
	return state


def CheckAddOrRemovePlayers(state):
	global playersToAdd, playersToRemove, playersToRemoveQueueOnly, addRemoveString
	if len(playersToAdd) > 0:
		if WANT_FILL in state['queue']:
			state = ReplaceWantFill(state, playersToAdd[0])
			state['queue'] = state['queue'] + playersToAdd[1:]
		else:
			state['queue'] = state['queue'] + playersToAdd
		state['stateUpdated'] = True
		playersToAdd = []
		if addRemoveString is not False:
			UpdateAddRemoveString()
			
	if len(playersToRemove) > 0:
		for player in playersToRemove:
			state = RemovePlayerFromState(state, player)
		playersToRemove = []
		if addRemoveString is not False:
			UpdateAddRemoveString()
			
	if len(playersToRemoveQueueOnly) > 0:
		changed = False
		for player in playersToRemoveQueueOnly:
			if player in state['queue']:
				state = RemovePlayerFromState(state, player)
				playersToRemoveQueueOnly = ListRemove(playersToRemoveQueueOnly, player)
				changed = True
		if changed and (addRemoveString is not False):
			UpdateAddRemoveString()
	return state


def SendStateToLobby(state, driver):
	if state['lobbyChannel'] is False:
		return
	
	driver.get('https://zero-k.info/Lobby/Chat?Channel={}'.format(state['lobbyChannel']))
	driver.implicitly_wait(0.5)
	
	cleanQueue = [name for name in state['queue'] if name != WANT_FILL]
	if len(cleanQueue) > 0:
		cleanQueue = ', '.join(cleanQueue)
	else:
		cleanQueue = 'empty'
	
	messageBox = driver.find_element(By.ID, 'chatbox')
	messageBox.clear()
	messageBox.send_keys('Queue: {}'.format(cleanQueue))
	messageBox.send_keys(Keys.RETURN)
	
	driver.get('https://zero-k.info/Tourney')
	driver.implicitly_wait(0.5)


def WriteAndPause(state, driver, waitTime):
	global forceUpdate
	doPrint = state['stateUpdated']
	if state['stateUpdated']:
		# Read stateUpdated before the state is written, otherwise it will
		# be overridden on state load.
		state['stateUpdated'] = False
	WriteState(state)
	UpdateUiStatus(state)
	if doPrint:
		# Print state after it is written, in case of crash.
		PrintState(state)
		SendStateToLobby(state, driver)
	updateTimer = 0
	while pauseMain or (updateTimer < waitTime and forceUpdate == 0):
		time.sleep(0.5)
		updateTimer = updateTimer + 0.5
	forceUpdate = max(0, forceUpdate - 1)
	state = ReadState()
	state = CheckAddOrRemovePlayers(state)
	if state['stateUpdated']:
		state['stateUpdated'] = False
		UpdateUiStatus(state)
		PrintState(state)
		SendStateToLobby(state, driver)
	return state


def AutonomousUpdateThread():
	global state
	state = InitializeState()
	driver = InitialiseWebDriver()
	
	UpdateUiStatus(state)
	
	print('Main thread started')
	while (not killMain):
		state = WriteAndPause(state, driver, state['postReadTimer'])
		if killMain:
			return
		state = SetupRequiredRooms(driver, state)
		state = CleanUpRooms(driver, state)
		#print('=========== Rooms Updated ===========')
		UpdateUiStatus(state)
	
		state = WriteAndPause(state, driver, state['postSetupTimer'])
		if killMain:
			return
		state = UpdateGameState(driver, state)
		#print('=========== State Updated ===========')


def TestThread():
	while (not killMain):
		print('pauseMain', pauseMain)
		time.sleep(1)


lastTextString = False
lastPlayerNames = False
tabIndex = 0

def SetupWindow():
	global statusString, addRemoveString
	global playersToAdd, playersToRemove, playersToRemoveQueueOnly
	window = tk.Tk()
	
	statusString = tk.StringVar()
	statusString.set("Status")
	
	pauseString = tk.StringVar()
	pauseString.set("PAUSED")
	
	addRemoveString = tk.StringVar()
	addRemoveString.set("")
	
	def Resume():
		global pauseMain, forceUpdate
		pauseMain = False
		forceUpdate = 2
		pauseString.set("ACTIVE")
		
	def Pause():
		global pauseMain
		pauseMain = True
		pauseString.set("PAUSED")
	
	def AddPlayer():
		global forceUpdate
		name = txtfld.get()
		txtfld.delete(0, tk.END)
		if len(name) > 0 and name not in playersToAdd:
			playersToAdd.append(name)
			UpdateAddRemoveString()
			forceUpdate = 2
	
	def RemovePlayer():
		global forceUpdate
		name = txtfld.get()
		txtfld.delete(0, tk.END)
		if len(name) > 0 and name not in playersToRemove:
			playersToRemove.append(name)
			UpdateAddRemoveString()
			forceUpdate = 2
	
	def RemovePlayerQueueOnly():
		global forceUpdate
		name = txtfld.get()
		txtfld.delete(0, tk.END)
		if len(name) > 0 and name not in playersToRemoveQueueOnly:
			playersToRemoveQueueOnly.append(name)
			UpdateAddRemoveString()
			forceUpdate = 2
	
	def TabPressed(event):
		global lastTextString, lastPlayerNames, tabIndex
		name = txtfld.get()
		if len(name) == 0 or state is False:
			return 'break'
		if name != lastTextString:
			playerNames = state['queue'].copy()
			for room, roomData in state['rooms'].items():
				if 'players' in roomData:
					playerNames = playerNames + roomData['players']
			playerNames = list(set(playerNames))
			playerNames = [x for x in playerNames if name in x]
			if len(playerNames) == 0:
				return 'break'
			lastPlayerNames = playerNames
			tabIndex = 0
		else:
			playerNames = lastPlayerNames
			tabIndex = (tabIndex + 1)%len(playerNames)
		
		lastTextString = playerNames[tabIndex]
		txtfld.delete(0, tk.END)
		txtfld.insert(0, lastTextString)
		return 'break'

	window.bind("<Tab>", TabPressed)
	
	offset = 20
	labelSpacing = 40
	spacing = 50
	fontSmall = ("Helvetica", 12)
	font      = ("Helvetica", 16)
	fontBig   = ("Helvetica", 24)
	
	label = tk.Label(window, textvariable=pauseString, font=fontBig, justify=tk.LEFT)
	label.place(x=20, y=offset)
	offset = offset + spacing
	
	btn = tk.Button(window, text="Resume", fg='blue', command=Resume, font=font, width=8)
	btn.place(x=20, y=offset)
	btn = tk.Button(window, text="Pause", fg='blue', command=Pause, font=font, width=8)
	btn.place(x=140, y=offset)
	btn = tk.Button(window, text="Print Stats", fg='blue', command=PrintBattles, font=font, width=12)
	btn.place(x=260, y=offset)
	offset = offset + spacing
	
	btn = tk.Button(window, text="Add", fg='blue', command=AddPlayer, font=font, width=8)
	btn.place(x=20, y=offset)
	btn = tk.Button(window, text="Remove", fg='blue', command=RemovePlayerQueueOnly, font=font, width=8)
	btn.place(x=140, y=offset)
	btn = tk.Button(window, text="Force Remove", fg='blue', command=RemovePlayer, font=font, width=12)
	btn.place(x=260, y=offset)
	
	label = tk.Label(window, textvariable=addRemoveString, font=fontSmall, justify=tk.LEFT)
	label.place(x=260, y=offset + 45)
	
	offset = offset + spacing
	
	txtfld = tk.Entry(window, text="Player Names", bd=5, font=font, width=18)
	txtfld.place(x=20, y=offset)
	offset = offset + labelSpacing
	
	label = tk.Label(window, textvariable=statusString, font=font, justify=tk.LEFT)
	label.place(x=20, y=offset)
	offset = offset + spacing
	
	window.title('Tournament Bot')
	window.geometry("500x500+1050+200")
	window.mainloop()
	
	pauseMain = True
	killMain = True
	PrintBattles()


def SetupThreads():
	mainThread = threading.Thread(target=AutonomousUpdateThread)
	mainThread.daemon = True
	mainThread.start()
	
	SetupWindow()


def CleanAgo(chatList):
	newList = []
	for text in chatList:
		if ' ago ' in text:
			newList.append(text[(text.find(' ago ') + 5):])
	return newList


def Test():
	state = {'lobbyChannel' : 'fc'}
	driver = InitialiseWebDriver()
	
	UpdateChat(driver, state)
	

SetupThreads()
#Test()

