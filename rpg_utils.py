#
# Copyright 2024 - Caspar Moritz Klein & Kseniia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
import json
import random
import math
data_path="datafiles/rpg_data.json"

def load_json():
    with open(data_path, "r") as f:
        return json.load(f)

def dump_json(data):
    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)

def sanitize_input(text:str):
    invalid_characters=['\'']
    new_text=""
    last_split=0
    print("testing: "+text[len(text):])
    for i in range(len(text)):
        if text[i] in invalid_characters:
            new_text=new_text+text[last_split:i]+'\''+text[i]
            last_split=i+1
    new_text+=text[last_split:]
    return new_text

def shorten_description(text:str):
    if len(text)<=100:
        return text
    return text[0:97]+"..."

# The stats returned by this are not the same as in the database, as I added the functionality for Cosmic Blessing here and gave the player some base Health and AD
def get_player_stat_dict(db_cursor,player_id):
    db_cursor.execute(f"SELECT * FROM user_current_stats WHERE user_id={player_id}")
    stats=db_cursor.fetchall()
    stats_dict={}
    for i in stats:
        stats_dict[i[3]]=i[4]
    db_cursor.execute("SELECT stat_name from stats")
    all_stats=db_cursor.fetchall()
    all_stats=[x[0] for x in all_stats]
    for i in all_stats:
        if not i in stats_dict:
            stats_dict[i]=0
    stats_dict["Health"]+=10
    stats_dict["Strength"]+=10
    for i in stats_dict.keys():
        if i!="Cosmic Blessing":
            stats_dict[i]=stats_dict[i]*(1+math.log2(1+stats_dict["Cosmic Blessing"]/100.0))


    return stats_dict

def apply_scalings(player_stats:dict,scalings:dict):
    sum=0
    for i in scalings.keys():
        if i in player_stats.keys():
            sum+=scalings[i]*player_stats[i]
    return sum


def init_combat(db_cursor,data:dict,player1:int,player2:int,automatic:bool = False):
    combat_key=f"{player1}x{player2}"
    data["player_fight_involvement"][str(player1)]=combat_key
    if not automatic:
        data["player_fight_involvement"][str(player2)]=combat_key

    data["active_fights"][combat_key]={}
    combat=data["active_fights"][combat_key]
    combat["automatic"]=automatic
    combat["players"]=[]
    
    # Cancel some other stuff the players are doing
    k=[]
    if str(player1) in data["combat_requests"]:
        if str(player1) in data["incoming_requests"][data["combat_requests"][str(player1)]]:
            data["incoming_requests"][data["combat_requests"][str(player1)]].remove(str(player1))
            if len(data["incoming_requests"][data["combat_requests"][str(player1)]])==0:
                del data["incoming_requests"][data["combat_requests"][str(player1)]]
        del data["combat_requests"][str(player1)]

    if not automatic and str(player2) in data["combat_requests"]:
        if str(player2) in data["incoming_requests"][data["combat_requests"][str(player2)]]:
            data["incoming_requests"][data["combat_requests"][str(player2)]].remove(str(player2))
            if len(data["incoming_requests"][data["combat_requests"][str(player2)]])==0:
                del data["incoming_requests"][data["combat_requests"][str(player2)]]
        del data["combat_requests"][str(player2)]

    for i in data["combat_scouting"].keys():
        if data["combat_scouting"][i]==str(player1) or ((not automatic) and data["combat_scouting"][i]==str(player2)):
            k.append(i)
    for i in k:
        del data["combat_scouting"][i] 


    # Initialize player 1
    p1_d={}
    p1_data=get_player_stat_dict(db_cursor,player1)
    p1_d["id"]=str(player1)
    p1_d["current_health"]=p1_data["Health"]
    p1_d["current_mana"]=3

    combat["players"].append(p1_d)

    # Initialize player 2
    p2_d={}
    p2_data=get_player_stat_dict(db_cursor,player2)
    p2_d["id"]=str(player2)
    p2_d["current_health"]=p2_data["Health"]
    p2_d["current_mana"]=3

    combat["players"].append(p2_d)

    # Init first turn
    db_cursor.execute(f"SELECT class_name FROM user_information WHERE user_id={player1}")
    p1=db_cursor.fetchone()
    combat["turn"] = 0
    combat["current_attack_pool"] = create_attack_pool(p1[0])



#gives (combat_name,enemy_id,your_turn?)
def get_combat_related_info(user_id):
    data=load_json()

    fight_name=data["player_fight_involvement"][str(user_id)]
    combat=data["active_fights"][fight_name]

    combatants=combat["players"]
    
    # Find some player-order specific things
    enemy_id=0
    my_turn=False
    if combatants[0]["id"]==str(user_id):
        enemy_id=combatants[1]["id"]
        if (combat["turn"]%2)==0:
            my_turn=True
    else:
        enemy_id=combatants[0]["id"]
        if (combat["turn"]%2)==1:
            my_turn=True
    return fight_name,enemy_id,my_turn

def check_player_in_combat(player_id:int):
    d=load_json()
    return str(player_id) in d["player_fight_involvement"]

def create_attack_pool(class_name: str):
    data = load_json()
    
    class_info=data["classes"][class_name]
    subclass = class_info["subclass"]
    alignment = class_info["alignment"]

    pool=[]

    # Füge den Standard Pool in den Auswahlpool hinzu
    pool.extend(data["attack_pools"]["general"])

    # Füge den Pool der Oberklasse in den Auswahlpool hinzu
    if subclass in data["attack_pools"]["subclass"]:
        pool.extend(data["attack_pools"]["subclass"][subclass])
    
    # Füge den Pool der Oberklasse in den Auswahlpool hinzu
    if alignment in data["attack_pools"]["alignment"]:
        pool.extend(data["attack_pools"]["alignment"][alignment])

    return random.sample(pool,3)
    