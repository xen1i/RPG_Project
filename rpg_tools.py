#
# Copyright 2025 - Caspar Moritz Klein & Xenia Kukushkina
#  Mini licence: Don't distribute the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and everyone willing to modify the code can get their own copy via the original source of distribution)
#
import discord
import discord.app_commands
from discord import ui
import json
import random
import time as time
import psycopg2

from config import load_config
import db_connect

from rpg_utils import *
from rpg_classes import *

plugin_name="RPG_tools"

class RPG_tools:
    client:discord.Client=None
    db:psycopg2.extensions.connection=None
    db_cur=None

    def reconnect(self):
        self.db=db_connect.connect(load_config())


    async def check_character_existing(self,user_id:int):
        player = player_class()
        try:
            if self.db.closed:
                a=1/0
            player.load_from_db(self.db_cur,user_id)
        except:
            self.reconnect()
            if self.db:
                self.db_cur=self.db.cursor()
                player.load_from_db(self.db_cur,user_id)
        finally:
            if not self.db:
                return None
            if player.id==-1:
                return None
            return player

    async def print_character_creation_prompt(self,ctx:discord.Interaction):
        print("processing new command")
        player= await self.check_character_existing(ctx.user.id)
        if player:
            return player
        else:
            await ctx.response.send_message("You have to create a character before you can play the game ;)",ephemeral=True)
            return None

    async def create_user_account(self,ctx:discord.Interaction, desired_character_name : str):
        if await self.check_character_existing(ctx.user.id):
            await ctx.response.send_message("You already have a character! You don't get an extra wurst.",ephemeral=True)
            return

        desired_character_name = sanitize_input(desired_character_name)

        if len(desired_character_name)>15:
            await ctx.response.send_message("Sadly, your desired name is too long. We go with a character limit of 15 letters.", ephemeral=True)
            return

        classes=[]
        sheet=class_choice_view()
        sheet.character_class.plugin=self
        sheet.character_class.options=[]
        #char_class = ui.Select(placeholder="Your Class",options=[])
        #Getting Character Classes

        if self.db_cur:
            self.db_cur.execute("SELECT c.class_id,c.class_name,c.class_description FROM class c")
            classes=self.db_cur.fetchall()
        for i in classes:
            sheet.character_class.append_option(discord.SelectOption(label=i[1],description=shorten_description(i[2]),value=i[0]))

        sheet.add_item(sheet.character_class)

        # Save name for later use
        data = load_json()
        if not "open_creation_prompts" in data:
            data["open_creation_prompts"]={}
        data["open_creation_prompts"][str(ctx.user.id)]=desired_character_name
        dump_json(data)


        await ctx.response.send_message(f"Nice, you will be known as {desired_character_name}, after you choose your class:",view=sheet,ephemeral=True)
    	
    async def show_rpg_help(self,ctx:discord.Interaction):
        create_char_line="Here are some commands you might need:\n"
        if self.check_character_existing(ctx.user.id):
            pass
        else:
            create_char_line="You can start playing by creating a character with /create_character!\n"+"After that you get access to some commands:\n"

        await ctx.response.send_message(create_char_line+
                                         "/move - moves your character to a new location\n"
                                         "/scavenge - used to scavenge for items at your current location, has a 5min cooldown\n"
                                         "/engage_battle - used to search for player battles at your current location\n",ephemeral=True)

    async def show_user_combat(self,ctx:discord.Interaction):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        data = load_json()

        # The user is in an active fight
        if str(player.id) in data["player_fight_involvement"]:
            fight_name,enemy_id,myturn=get_combat_related_info(player.id)
            combat=data["active_fights"][fight_name]

            enemy=await self.check_character_existing(int(enemy_id))

            infoEmbed=discord.Embed()

            if myturn:
                infoEmbed.title="Your possible Actions:"
                desc=""
                counter=1
                stats_dict=get_player_stat_dict(self.db_cur,player.id)
                for i in combat["current_attack_pool"]:
                    att = attack()
                    att.id=i
                    att.load_from_db(self.db_cur)
                    desc+=f"{counter}: {att.name} - {att.description}\n"
                    if len(att.physical_damage)>0:
                        scalings=att.physical_damage
                        desc+=" - Deals physical damage\n"
                        desc+="  - "+", ".join([f"{i}: {int(scalings[i]*100)}%" if scalings[i]!=0 else "" for i in scalings.keys()])+"\n"
                    if len(att.magic_damage)>0:
                        scalings=att.magic_damage
                        desc+=" - Deals magic damage\n"
                        desc+="  - "+", ".join([f"{i}: {int(scalings[i]*100)}%" if scalings[i]!=0 else "" for i in scalings.keys()])+"\n"
                    if att.can_crit:
                        crit_chance=stats_dict["Critical Hit Chance"]
                        desc+=f"- Can critical strike: {round((1-0.5**(crit_chance/80.0))*100,2)}% (depends on your crit chance)\n"
                    if att.is_piercing:
                        pen=stats_dict["Wielding"]*0.5
                        if att.can_crit:
                            desc+=f" and pierce through armor/ willpower by roughly {pen} points of resistance\n"
                        else:
                            desc+=f" - Can piece through armor/ willpower by roughly {pen} points of resistance\n"
                    #if att.can_crit or att.is_piercing:
                    #    desc+="\n"
                    desc+="\n"
                    counter+=1
                infoEmbed.description=desc
            else:
                infoEmbed.title="It is not your turn"
                infoEmbed.description="You have to wait until your opponent makes their move."

            await ctx.response.send_message(f"You are in a fight with {enemy.name}.",embed=infoEmbed,ephemeral=True)
            return
        
        # The user has send an open request
        if str(player.id) in data["combat_requests"]:
            contender_name="Sir-I-cannot-initialize-the-database-connection-alot"
            if self.db_cur:
                cr=data["combat_requests"]
                self.db_cur.execute(f"SELECT user_name FROM character where user_id={str(cr[str(ctx.user.id)])}")
                contender_name=self.db_cur.fetchone()[0]

            await ctx.response.send_message(f"You have challenged {contender_name} to a battle, they haven't answered yet. You can cancel the challenge by using the /challenge_player command without any arguments.",ephemeral=True)
            return

        # The user has received an open request
        if str(player.id) in data["incoming_requests"]:
            contender_name=["Mary-van-I-cannot-initialize-the-database-connection"]
            if self.db_cur:
                ir=data["incoming_requests"]
                contender_name=[]
                q_str=" OR user_id=".join(ir[str(ctx.user.id)])
                self.db_cur.execute(f"SELECT user_name FROM character where user_id={q_str}")
                for i in range(self.db_cur.rowcount):
                    contender_name.append(self.db_cur.fetchone()[0])

            await ctx.response.send_message(f"You have been challenged by these people: {str(contender_name)}. You can accept by using the /challenge_player command on them. If you want to, you can also ignore the request(s)",ephemeral=True)
            return

        # The user is currently scouting for combat
        if str(player.location) in data["combat_scouting"] and data["combat_scouting"][str(player.location)]==str(player.id):
            loc_name="I-cannot-initialize-the-database-connection-city"
            if self.db_cur:
                self.db_cur.execute(f"SELECT loc_name FROM user_information where user_id={player.id}")
                loc_name=self.db_cur.fetchone()[0]
            await ctx.response.send_message(f"{player.name} is currently scouting for combat at {loc_name}. You can stop scouting by using the /scout_battle command again",ephemeral=True)
            return
        
        await ctx.response.send_message(f"{player.name} is neither challenged, challenges or battles, you might wanna change that.",ephemeral=True)

    async def show_user_info(self,ctx:discord.Interaction):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        print("showing player data",player)
        level_progress=""
        a=player.level_progress/(player.level+1)
        level_progress = f" ({round(a*100,1)}% towards next level)"
        info_embed=discord.Embed(title=f"{player.name} - Level {player.level}{level_progress}")
        stats_dict=get_player_stat_dict(self.db_cur,player.id)
        self.db_cur.execute("SELECT stat_name,stat_description from stats ORDER BY stat_name ASC")
        all_stats=self.db_cur.fetchall()
        all_stats=[(x[0],x[1]) for x in all_stats]
        desc=""
        for i in all_stats:
            if i[0] in stats_dict:
                desc+=f"- {i[0]}: {stats_dict[i[0]]}\n"
            else:
                desc+=f"- {i[0]}: 0\n"
            desc+=f" - {i[1]}\n"
        info_embed.description=desc

        # Hier noch ne section zu den items, TODO
        item_field_desc=""


        await ctx.response.send_message("Your info",ephemeral=True,embed=info_embed)

    async def show_user_location(self,ctx:discord.Interaction):
        player=await self.print_character_creation_prompt(ctx)
        print("location debug: "+str(player))
        if not player:
            return
        location_info=[]
        cur_location=None
        if self.db_cur:
            self.db_cur.execute(f"SELECT loc_id,loc_name,loc_description,loc_level FROM location where loc_level<={player.level} and loc_id!={player.location}")
            location_info=self.db_cur.fetchall()
            self.db_cur.execute(f"SELECT l.loc_id,l.loc_name,l.loc_description,l.loc_level FROM location l WHERE {player.location}=l.loc_id")
            cur_location=self.db_cur.fetchone()
        LocationEmbed=discord.Embed(title=f"{player.name}'s location")
        LocationEmbed.description=f"""
        {player.name}'s location is\n
        - {cur_location[0]}: {cur_location[1]} - Level {cur_location[3]}\n
              {cur_location[2]}
        """
        world_location_string="Other locations on the game map include:\n"
        for i in location_info:
            world_location_string+=f"- {i[0]}: {i[1]} - Level {i[3]}\n - {i[2]}\n"

        LocationEmbed.add_field(name="World Locations",value=world_location_string)
        await ctx.response.send_message("Here is your information:",embed=LocationEmbed,ephemeral=True)

    async def show_global_stats(self,ctx:discord.Interaction):
        if self.db.closed:
            self.reconnect()

        stats_report=""

        #Finding highest player level
        self.db_cur.execute("SELECT MAX(user_level) FROM character;")
        max_level=self.db_cur.fetchone()[0]

        #Finding players with highest level
        self.db_cur.execute("""
                            SELECT user_id FROM character WHERE user_level=%s;
                            """,(max_level,))
        highest_users=self.db_cur.fetchall()

        displayed_user=random.choice(highest_users)[0]
        self.db_cur.execute("""
                                SELECT class_name,loc_name FROM user_information WHERE user_id=%s
                            """,(displayed_user,))
        random_highest_user_info=self.db_cur.fetchone()

        stats_report+= f"""The maximum level any champion has is {max_level}. There is/are {len(highest_users)} champions with this level.
        A {random_highest_user_info[0]} of that level is located at {random_highest_user_info[1]}"""
        if displayed_user==ctx.user.id:
            stats_report+="""\nOh wait, that is you!"""

        await ctx.response.send_message(stats_report,ephemeral=True)

    async def move_user_to_location(self,ctx:discord.Interaction,target_location:str):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if await self.print_player_in_combat_prompt(ctx):
            return
        target_location_r=target_location
        target_location= sanitize_input(target_location)
        loc=None
        no_loc_found = lambda: ctx.response.send_message(f"There is no location like that, that you are able to travel to. You searched for {target_location_r}.",ephemeral=True)
        if self.db_cur:
            if target_location.isnumeric():
                self.db_cur.execute(f"SELECT loc_id, loc_name FROM location WHERE loc_level<={player.level} and loc_id={int(target_location)}")
                if self.db_cur.rowcount==0:
                    await no_loc_found()
                    return
                loc=self.db_cur.fetchone()
            else:
                self.db_cur.execute(f"SELECT loc_id, loc_name FROM location WHERE loc_level<=%s and loc_name=%s",(player.level,str(target_location)))
                if self.db_cur.rowcount==0:
                    await no_loc_found()
                    return
                loc=self.db_cur.fetchone()
            print(f"UPDATE character SET located = {loc[0]} WHERE user_id={ctx.user.id}")
            self.db_cur.execute(f"UPDATE character SET located = {loc[0]} WHERE user_id={ctx.user.id};")
            self.db.commit()
            await ctx.response.send_message(f"{player.name} moved to {loc[1]}!")
        else:
            await ctx.response.send_message(f"I, the bot, am not able to connect to the database :(")
            return
        
    async def search_for_items(self,ctx:discord.Interaction):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if await self.print_player_in_combat_prompt(ctx):
            return
        data = load_json()
        if not "last_scavenge" in data:
            data["last_scavenge"] = {}
        utime=time.time()
        if not str(player.id) in data["last_scavenge"]:
            pass # We can scavenge
        else:
            timediff=utime-data["last_scavenge"][str(player.id)]
            if timediff<300:
                await ctx.response.send_message(f"You cannot loot the location now. You have {int(300-timediff)}s left on the cooldown.",ephemeral=True)
                return
        data["last_scavange"][str(player.id)]=utime
        # Here comes the scavanging
        print("Fetching Items:")
        item_pool=[] ## [(index_db_ip,weight)]
        db_item_pool=[]
        if self.db_cur:
            self.db_cur.execute(f"SELECT * FROM valid_item_pools WHERE user_id=%s",(ctx.user.id,))
            db_item_pool=self.db_cur.fetchall()
            for i in range(len(db_item_pool)):
                level_weights=[0.4,0.7,1,0.2]
                print(db_item_pool[i])
                item_pool.append((i,level_weights[min(3,max(0,db_item_pool[i][6]+2))]*db_item_pool[i][5]))
            summed_weight=sum([x[1] for x in item_pool])
            rand_choice=random.random()*summed_weight
            chosen=None
            for i in range(len(item_pool)):
                if rand_choice<item_pool[i][1]:
                    chosen=db_item_pool[item_pool[i][0]]
                    break
                rand_choice-=item_pool[i][1]
            if chosen:
                print(chosen)
                #The selected item is already present in the players inventory
                if chosen[7]!=None:
                    self.db_cur.execute(f"UPDATE owns SET item_amount=%s WHERE item_id=%s and user_id=%s;",(chosen[7]+1,chosen[2],chosen[0]))
                    self.db.commit()
                #The selected item is new to this player
                else:
                    self.db_cur.execute(f"INSERT INTO owns VALUES (%s,%s,%s,%s);",(chosen[2],chosen[0],1,False))
                    self.db.commit()

                item_embed=discord.Embed(title=chosen[3],description=chosen[8])

                await ctx.response.send_message(f"{chosen[1]} has found an item:",embed=item_embed,ephemeral=True)
            else:
                await ctx.response.send_message(f"I, the bot, am not able to randomly select an item, sorry",ephemeral=True)
        else:
            await ctx.response.send_message(f"I, the bot, am not able to connect to the database, sorry",ephemeral=True)

        dump_json(data)

    async def print_player_in_combat_prompt(self,ctx:discord.Interaction):
        check=check_player_in_combat(ctx.user.id)
        if check:
            await ctx.response.send_message(f"Your character is in combat, you can't do that right now.",ephemeral=True)
        return check

    async def engage_local_battle(self,ctx:discord.Interaction):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if await self.print_player_in_combat_prompt(ctx):
            return
        data=load_json()
        

        location_name="<The land without database connections>"
        if self.db_cur:
            self.db_cur.execute(f"SELECT * FROM user_information WHERE user_id={player.id}") # 3 for location name
            location_name=self.db_cur.fetchone()[3]
        
        if str(player.location) in data["combat_scouting"]:
            combatant_id=data["combat_scouting"][str(player.location)]
            combatant=await self.check_character_existing(combatant_id)
            combatant_name=""
            if combatant:
                combatant_name=combatant.name
            else:
                del data["combat_scouting"][str(player.location)]
                data["combat_scouting"][str(player.location)]=str(player.id)
                await ctx.response.send_message(f"{player.name} is now scouting for battle at {location_name}.",ephemeral=True)
                dump_json()
                return

            if combatant_id==str(player.id):
                del data["combat_scouting"][str(player.location)]
                await ctx.response.send_message(f"{player.name} is no longer scouting for battle at {location_name}.",ephemeral=True)
            else:
                init_combat(self.db_cur,data,combatant_id,player.id)
                del data["combat_scouting"][str(player.location)]
                await ctx.response.send_message(f"{combatant_name} was already scouting at {location_name}. {player.name} is challenging them!",ephemeral=True)
                await ctx.channel.send(f"Battle emerges between {self.client.get_user(combatant_id).mention} and {ctx.user.mention}! Pick your favorite and cheer them on!")
        else: 
            #data["combat_scouting"][str(player[3])]=str(player[0])
            #await ctx.response.send_message(f"{player[2]} is now scouting for battle at {location_name}.",ephemeral=True)
            self.db_cur.execute(f"SELECT user_id,user_name FROM character WHERE located=%s and (not user_id=%s) and user_level<=%s",(player.location,player.id,player.level+2))
            if self.db_cur.rowcount==0:
                await ctx.response.send_message("There is no one in your league, who is currently at your position",ephemeral=True)
            else:
                combatants=self.db_cur.fetchall()
                enemy=random.choice(combatants)
                init_combat(self.db_cur,data,player.id,enemy[0],automatic=True)
                await ctx.response.send_message(f"{enemy[1]}-Bot was already scouting at {location_name}. {player.name} is challenging them!")
                await ctx.channel.send(f"Battle emerges between {enemy[1]}-Bot and {ctx.user.mention}! Pick your favorite and cheer them on!")

        dump_json(data)
        
    async def request_user_duel(self,ctx:discord.Interaction,target_player:str):
        # We make sure the caller has a character and is not in combat
        print("I recognize the duel attempt")
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if await self.print_player_in_combat_prompt(ctx):
            return
        target_player_r=target_player
        target_player=sanitize_input(target_player)
        
        # We make sure the target player exists
        target_id=0
        target=None
        if self.db_cur:
            self.db_cur.execute(f"SELECT user_id,user_level,user_name FROM character WHERE user_name='{target_player}'")
            if self.db_cur.rowcount<1:
                await ctx.response.send_message(f"There is no player named {target_player_r}",ephemeral=True)
                return
            target=self.db_cur.fetchone()
            target_id=target[0]
        else:
            await ctx.response.send_message("I cannot connect to the database, sry",ephemeral=True)
            return

        # We load data
        data=load_json()
        accepted_req=False

        id=str(player.id)

        # The caller has incoming combat requests
        if id in data["incoming_requests"]:
            for i_idx in range(len(data["incoming_requests"][id])):
                i=data["incoming_requests"][id][i_idx]
                
                # The incoming request from the person the caller is trying to challenge -> accept
                if str(target_id)==i:
                    cancelled_req=""
                    # The caller had an outgoing combat request
                    if id in data["combat_requests"]:

                        # We find all info about the old target
                        old_target_id=data["combat_requests"][id]
                        old_target=await self.check_character_existing(old_target_id)
                        if old_target:
                            cancelled_req=old_target.name
                    init_combat(self.db_cur,data,target_id,player.id)

                    accepted_req=True

                    if cancelled_req:
                        await ctx.response.send_message(f"You have accepted the challenge and are now in battle with {target[2]}! This cancels your request to {name}.",ephemeral=True)
                    else:
                        await ctx.response.send_message(f"You have accepted the challenge and are now in battle with {target[2]}!",ephemeral=True)
                    await ctx.channel.send(f"Battle emerges between {self.client.get_user(target_id).mention} and {ctx.user.mention}! Pick your favorite and cheer them on!")
                    break
                # Else 10% to check if the player requesting still exists, 10% to save performance
                elif random.random()>0.9:
                    if not self.check_character_existing(i):
                        # If the player doesn't exist, delete all related requests to the caller
                        data["incoming_requests"][id].remove(i)
                        if i in data["combat_requests"]:
                            del data["combat_requests"][i]
            # If we cleared the list of requests, delete the entry
            if id in data["incoming_requests"] and len(data["incoming_requests"][id])==0:
                del data["incoming_requests"][id]

        # We could not accept an incoming request, so we issue a new one
        if not accepted_req:
            old_target=None
            # The caller already had issued a request
            if id in data["combat_requests"]:
                # We find all info about the old target
                old_target_id=data["combat_requests"][id]
                old_target=await self.check_character_existing(old_target_id)
                
                # Delete the request for old target
                if str(old_target_id) in data["incoming_requests"]:
                    if len(data["incoming_requests"][str(old_target_id)])<=1:
                        del data["incoming_requests"][str(old_target_id)]
                    else:
                        data["incoming_requests"][str(old_target_id)].remove(id)
                name="<deleted-player>"
                if old_target:
                    name=old_target.name
                # If old target==new target, completely delete the request
                if str(old_target_id)==str(target_id):
                    del data["combat_requests"][id]

                    await ctx.response.send_message(f"You cancelled the combat request to {name}",ephemeral=True)
                else:
                    data["combat_requests"][id]=str(target_id)
                    if str(target_id) in data["incoming_requests"]:
                        data["incoming_requests"][str(target_id)].append(id)
                    else:
                        data["incoming_requests"][str(target_id)]=[id]
                    await ctx.response.send_message(f"You challenged {target[2]} to a battle. This cancelled your duel-request with {name}",ephemeral=True)
            else:
                data["combat_requests"][id]=str(target_id)
                if str(target_id) in data["incoming_requests"]:
                    data["incoming_requests"][str(target_id)].append(id)
                else:
                    data["incoming_requests"][str(target_id)]=[id]
                await ctx.response.send_message(f"You challenged {target[2]} to a battle.",ephemeral=True)

        dump_json(data)

    async def user_equip_item(self,ctx:discord.Interaction,item:str):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if await self.print_player_in_combat_prompt(ctx):
            return
        item_info=None
        item_r=item
        item=sanitize_input(item_r)

        if self.db_cur:
            if item.isnumeric():
                self.db_cur.execute(f"SELECT equipped,equippable,item_name,item_id FROM character NATURAL JOIN owns NATURAL JOIN item WHERE user_id={str(player.id)} and item_id={item}")
                if self.db_cur.rowcount>0:
                    item_info=self.db_cur.fetchone()
            else:
                self.db_cur.execute(f"SELECT equipped,equippable,item_name,item_id FROM character NATURAL JOIN owns NATURAL JOIN item WHERE user_id={str(player.id)} and item_name='{item}'")
                if self.db_cur.rowcount>0:
                    item_info=self.db_cur.fetchone() 
        else:
            await ctx.response.send_message("I cannot connect to the db, ask the admin to restart me",ephemeral=True)
            return
        
        if item_info==None:
            await ctx.response.send_message(f"{player.name} does not have an Item like that!",ephemeral=True)
            return

        if item_info[1]==0:
            await ctx.response.send_message(f"{player.name} has a {item_info[2]}, but it's not an equippable item.",ephemeral=True)
            return

        if not item_info[0]:
            self.db_cur.execute(f"SELECT item_id FROM character NATURAL JOIN owns NATURAL JOIN item WHERE user_id={str(player.id)} and equipped and equippable={item_info[1]}")
            if self.db_cur.rowcount>0:
                old_equipped=self.db_cur.fetchone()
                self.db_cur.execute(f"UPDATE owns SET equipped=False WHERE user_id={player.id} and item_id={old_equipped[0]}")
        self.db_cur.execute(f"UPDATE owns SET equipped=True WHERE user_id={player.id} and item_id={item_info[3]}")
        self.db.commit()
        await ctx.response.send_message(f"{player.name} has successfully equipped {item_info[2]}!",ephemeral=True)

    async def user_use_attack(self,ctx:discord.Interaction,move:str):
        player=await self.print_character_creation_prompt(ctx)
        if not player:
            return
        if not check_player_in_combat(player.id):
            await ctx.response.send_message("You cannot do that, as you are not in combat!",ephemeral=True)
            return

        data=load_json()
        move_r=move
        move=sanitize_input(move_r)
        combat_name, enemy_id, myturn = get_combat_related_info(player.id)
        if not myturn:
            await ctx.response.send_message("It is not your turn, you have to wait for your opponent to make theirs first.",ephemeral=True)
            return
        
        if not move.isnumeric() or int(move)<1 or int(move)>3:
            await ctx.response.send_message("The move-number you entered is not valid.",ephemeral=True)
            return
        combat=data["active_fights"][combat_name]
    
        att = attack()
        att.id=combat["current_attack_pool"][int(move)-1]
        att.load_from_db(self.db_cur)

        player_stats=get_player_stat_dict(self.db_cur,player.id)
        enemy_stats=get_player_stat_dict(self.db_cur,enemy_id)

        #Calculate Damage
        dealt_physical,dealt_magical,crits,dodges=calc_ability_damage(att,player_stats,enemy_stats)

        dealt_damage = dealt_physical+dealt_magical

        print(f"total dealt: {dealt_damage}")
        
        enemy_cur=combat["players"][(combat["turn"]+1)%2]
        enemy_cur["current_health"]-=dealt_damage

        kills=enemy_cur["current_health"]<=0
        
        self.db_cur.execute(f"SELECT user_id,class,user_name,user_level FROM character WHERE user_id={enemy_id}")
        enemy=self.db_cur.fetchone()

        print("combat: "+str(combat))

        if "automatic" in combat and combat["automatic"]:
            enemy=(enemy[0],enemy[1],enemy[2]+"-Bot",enemy[3])

        crit_prefix=""
        if crits:
            crit_prefix="Crit! "

        if dealt_damage!=0:
            dmgs=[]
            dealt_damage=""
            if dealt_physical:
                dmgs.append(f"{round(dealt_physical,2)} Physical Damage")
            if dealt_magical:
                dmgs.append(f"{round(dealt_magical,2)} Magical Damage")
            dealt_damage=" + ".join(dmgs)


        if kills:
            level_up = ""
            if "automatic" in combat and combat["automatic"] and enemy[3]>=player.level:
                #Get 1 xp and level up if player.xp == player.level
                level_up=grant_player_xp(self.db_cur,player)
            await ctx.response.send_message(crit_prefix+f"{player.name} used '{att.name}' and dealt {dealt_damage} damage to and thus killed {enemy[2]}. {player.name} wins the combat!\n"+level_up)
            combatants=combat["players"]
            c1=combatants[0]["id"]
            c2=combatants[1]["id"]
            turn=combat["turn"]
            self.db_cur.execute(f"INSERT INTO battlelog (initiator_id,opponent_id,result) VALUES (%s,%s,%s)",(c1,c2,2-2*(turn%2)))
            self.db.commit()
            del data["player_fight_involvement"][str(player.id)]
            if not ("automatic" in combat and combat["automatic"]):
                del data["player_fight_involvement"][str(enemy[0])]
            del data["active_fights"][combat_name]
        else:
            if dodges:
                await ctx.response.send_message(crit_prefix+f"{player.name} used '{att.name}', but {enemy[2]} dodged the attack")
            else:
                await ctx.response.send_message(crit_prefix+f"{player.name} used '{att.name}' and dealt {dealt_damage} damage to {enemy[2]}")
            combat["turn"]+=1
            if "automatic" in combat and combat["automatic"]:
                combat["current_attack_pool"]=create_attack_pool(self.db_cur,player.player_class)
            else:
                combat["current_attack_pool"]=create_attack_pool(self.db_cur,enemy[1])
        
        if not kills and "automatic" in combat and combat["automatic"]:
            movenum=random.choice(range(3))
            att_pool=create_attack_pool(self.db_cur,enemy[1])
            att = attack()
            att.id=att_pool[movenum]
            att.load_from_db(self.db_cur)        
            dealt_physical,dealt_magical,crits,dodges=calc_ability_damage(att,enemy_stats,player_stats)

            dealt_damage = dealt_physical+dealt_magical

            print(f"total dealt: {dealt_damage}")
        
            player_cur=combat["players"][0]
            player_cur["current_health"]-=dealt_damage

            kills=player_cur["current_health"]<=0

            crit_prefix=""
            if crits:
                crit_prefix="Crit! "

            if dealt_damage!=0:
                dmgs=[]
                dealt_damage=""
                if dealt_physical:
                    dmgs.append(f"{round(dealt_physical,2)} Physical Damage")
                if dealt_magical:
                    dmgs.append(f"{round(dealt_magical,2)} Magical Damage")
                dealt_damage=" + ".join(dmgs)
                
            if kills:
                await ctx.channel.send(crit_prefix+f"{enemy[2]} used '{att.name}' and dealt {dealt_damage} damage to and thus killed {player.name}. {enemy[2]} wins the combat!")
                combatants=combat["players"]
                c1=combatants[0]["id"]
                c2=combatants[1]["id"]
                turn=combat["turn"]
                self.db_cur.execute(f"INSERT INTO battlelog (initiator_id,opponent_id,result) VALUES ({c1},{c2},{2-2*(turn%2)})")
                self.db.commit()
                del data["player_fight_involvement"][str(player.id)]
                del data["active_fights"][combat_name]
            else:
                if dodges:
                    await ctx.channel.send(crit_prefix+f"{enemy[2]} used '{att.name}', but {player.name} dodged the attack")
                else:
                    await ctx.channel.send(crit_prefix+f"{enemy[2]} used '{att.name}' and dealt {dealt_damage} damage to {player.name}")
                combat["turn"]+=1

        dump_json(data)



def link(commandTree:discord.app_commands.CommandTree, db):
    inst=RPG_tools()
    inst.client=commandTree.client
    inst.db=db
    inst.db_cur=db.cursor()
 
   # inst.client.event(inst.on_raw_reaction_add)
   # inst.client.event(inst.on_raw_reaction_remove)

   # com_sr=discord.app_commands.Command(name="setup_selfrole",description="Use this command to define selfrole-emojis on specified messages.",callback=inst.selfrole)
   # com_sr.add_check(discord.app_commands.checks.has_permissions(administrator=True))

    com_help=discord.app_commands.Command(name="rpg_help",description="Display the list of available commands and how to use them",callback=inst.show_rpg_help)
    com_user_info=discord.app_commands.Command(name="my_info",description="View your stats and items.",callback=inst.show_user_info)
    com_user_location=discord.app_commands.Command(name="my_location",description="View information about your location",callback=inst.show_user_location)
    com_global_statistics=discord.app_commands.Command(name="rpg_statistics",description="View statistics about the game",callback=inst.show_global_stats)
    com_user_move=discord.app_commands.Command(name="move",description="Move to another location",callback=inst.move_user_to_location)
    com_scavange=discord.app_commands.Command(name="scavange",description="Search for items at your current location. This has a 5min cooldown.",callback=inst.search_for_items)
    com_combat_local=discord.app_commands.Command(name="scout_battle",description="Start looking for some combat opportunities at your location.",callback=inst.engage_local_battle)
    com_combat_duel=discord.app_commands.Command(name="challenge_player",description="Challenge a fellow player to a one vs one.",callback=inst.request_user_duel)
    com_combat_info=discord.app_commands.Command(name="my_combat_situation",description="View information about your combat or incoming/outgoing combat requests",callback=inst.show_user_combat)
    com_user_equip=discord.app_commands.Command(name="equip",description="Use this to equip the items from your inventory, you can see them by using /my_info",callback=inst.user_equip_item)
    com_user_attack=discord.app_commands.Command(name="use_move",description="Enter the number of the attack you've found in /my_combat_situation.",callback=inst.user_use_attack)

    com_user_create=discord.app_commands.Command(name="create_character",description="Enter your name, press enter and choose a class afterwards. Start playing now!",callback=inst.create_user_account)



    commandTree.add_command(com_help) # incomplete
    commandTree.add_command(com_user_info) # level, stats
    commandTree.add_command(com_user_location) # how to get to which locations
    commandTree.add_command(com_global_statistics) # incomplete
    commandTree.add_command(com_user_move) # done
    commandTree.add_command(com_scavange) # done
    commandTree.add_command(com_combat_local) # done
    commandTree.add_command(com_combat_duel) # done
    commandTree.add_command(com_combat_info) # implemented, but unsatisfying
    commandTree.add_command(com_user_equip) # wack
    commandTree.add_command(com_user_attack) # ok
    commandTree.add_command(com_user_create) # done




   # commandTree.add_command(com_sr)

# This has to be here because of some import shenanigans
def calc_ability_damage(att : attack, player_stats,enemy_stats):
    dealt_physical_raw=apply_scalings(player_stats,att.physical_damage)
    dealt_magical_raw=apply_scalings(player_stats,att.magic_damage)

    print(f"raw damage: {dealt_physical_raw} {dealt_magical_raw}")

    crits = random.random()>0.5**(player_stats["Critical Hit Chance"]/80.0)
    if crits:
        dealt_physical_raw*=1+math.log2(player_stats["Critical Hit Damage"]+1)
        dealt_magical_raw*=1+math.log2(player_stats["Critical Hit Damage"]*0.9+1)
    print(f"raw damage after crit: {dealt_physical_raw} {dealt_magical_raw}")


    armor_after_pen=max(0,enemy_stats["Armor"]-player_stats["Wielding"]*0.6)
    magir_after_pen=max(0,enemy_stats["Willpower"]-player_stats["Wielding"]*0.4-player_stats["Luck"]*0.1)

    print(f"resistances: {armor_after_pen} {magir_after_pen}")

    dodges= random.random()<(1-(0.5**(enemy_stats["Dexterity"]/80.0)))/4

    dealt_physical=dealt_physical_raw/(1+math.sqrt(armor_after_pen)/8)
    dealt_magical=dealt_magical_raw/(1+math.sqrt(magir_after_pen)/6)

    print(f"dealt: {dealt_physical} {dealt_magical}")
    if dodges:
        dealt_physical,dealt_magical=0,0
    return dealt_physical,dealt_magical,crits,dodges
