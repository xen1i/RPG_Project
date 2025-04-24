#
# Copyright 2024 - Caspar Moritz Klein & Xenia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
# This file exists to break circular dependency; do not import from other files to this file
import json

data_path="datafiles/rpg_data.json"

def load_json():
    with open(data_path, "r") as f:
        return json.load(f)

def dump_json(data):
    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)