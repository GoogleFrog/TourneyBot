from pprint import pprint
import json

import os
from pathlib import Path


if __name__ == '__main__':
    directory = Path('..') / 'archive'
    def filter(file: Path):
        return file.is_file() and file.name.startswith("2024") and file.suffix == '.json'
    files = [x for x in directory.iterdir() if filter(x)]

    players = set()
    for file in files:
        with open(file) as f:
            j = json.load(f)
            games = j['completedGames']
            for entry, value in games.items():
                players.add(value['winner'])
                players.add(value['loser'])

    print(players)
    print("number of players:,",len(players))
    print("number of files,", len(files))
