#
# Copyright 2024 - Caspar Moritz Klein & Xenia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
import random
import math
from rpg_json_utils import load_json,dump_json
from rpg_classes import player_class

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
    p1_d["current_health"]=p1_data["Health"]*3+100
    p1_d["current_mana"]=3

    combat["players"].append(p1_d)

    # Initialize player 2
    p2_d={}
    p2_data=get_player_stat_dict(db_cursor,player2)
    p2_d["id"]=str(player2)
    p2_d["current_health"]=p2_data["Health"]*3+100
    p2_d["current_mana"]=3

    combat["players"].append(p2_d)

    player1_obj=player_class()
    player1_obj.load_from_db(db_cursor,player1)

    # Init first turn
    combat["turn"] = 0
    combat["current_attack_pool"] = create_attack_pool(db_cursor,player1_obj.player_class)



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

def create_attack_pool(db_cur,class_id : int):
    
    db_cur.execute("SELECT attack_id FROM class_full_attack_pool WHERE class_id=%s",(class_id,))

    pool=db_cur.fetchall()

    pool=random.sample(pool,3)

    print("I created a pool :D ",pool)

    pool = [i[0] for i in pool]

    return pool

def db_exec_fetchone(db_cur,query):
    db_cur.execute(query)
    if db_cur.rowcount!=1:
        print(f"db_exec_fetchone got {db_cur.rowcount} results instead of one, this should not happen")
        return None
    return db_cur.fetchone()

def db_get_attack_by_name(db_cur,name):
    db_cur.execute(f"SELECT * FROM attack WHERE attack.name='{name}'")
    return db_cur.fetchone()

def grant_player_xp(db_cur, player : player_class):
    if player.level_progress+1>=player.level:
        # Increase level by 1, set progress to 0
        db_cur.execute(f"UPDATE character SET user_level=%s,user_level_progression=0 WHERE user_id=%s",(player.level+1,player.id))
        player.level+=1
        player.level_progress=0
    else:
        # Increase progress by 1
        db_cur.execute(f"UPDATE character SET user_level_progression=%s WHERE user_id=%s",(player.level_progress+1,player.id))
        player.level_progress+=1
        return ""