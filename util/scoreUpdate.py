import sys
import os
import json
import main as project
from pprint import pprint

if __name__ == '__main__':
    score_file = None
    data_file = None
    output_file = "scoreOutput.json"

    # argument catching
    args = sys.argv
    i = 1
    if len(args) == 1:
        print("Launch args: [-i input-score-file] [-s state-file] [-o output-score-file]")
        exit()
    while len(args) > i+1:
        option = args[i]
        value = args[i+1]
        if option[0] != '-':
            print("[%s] is not an option" % (args[i]))
            exit()
        match option[1:]:
            case 'i':
                # input score file
                score_file = value
            case 's':
                # new state file
                data_file = value
            case 'o':
                # define output file
                output_file = value
            case other:
                print("[%s] is an invalid argument! value: %s" % (option,value))
                exit()
        i += 2
    
    # import score
    score = None
    if score_file is not None:
        with open(score_file, 'r') as f:
            score = json.load(f)
    else:
        score = dict()
    print("loaded scores:",score)

    # grab new state data and process
    state = None
    if data_file is not None:
        with open(data_file, 'r') as f:
            state = json.load(f)
        
        players = set()
        playerStreaks = dict()
        scorekeys = score.keys()
        for game in state["completedGames"].items():
            d = game[1]
            players.add(d['winner'])
            players.add(d["loser"])
        for p in players:
            playerStreaks[p] = 0
            if p not in scorekeys:
                score[p] = 0
        for game in state["completedGames"].items():
            data = game[1]
            winner = data["winner"]
            loser = data["loser"]

            # loser score update
            score[loser] += 1

            # winner score update
            score[winner] += (2 + playerStreaks[loser])

            playerStreaks[loser] = 0
            playerStreaks[winner] += 1

    # save score
    if score is not None:
        with open(output_file, 'w') as output:
            json.dump(score, output, indent=4)
    
    # print scores to console
    scorelist = list(score.items())
    scorelist.sort(key=lambda x : x[1], reverse=True)
    print("Current Scoreboard:")
    counter = 0
    for data in scorelist:
        if counter == 10:
            print("more:","[spoiler]", sep='\n')
            counter = 20
        player = data[0]
        s = data[1]
        print("* @%s: %s" % (player, s))
        counter += 1
    if counter > 19:
        print("[/spoiler]")
