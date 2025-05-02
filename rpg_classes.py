#
# Copyright 2025 - Caspar Moritz Klein & Xenia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
from rpg_json_utils import load_json,dump_json
import discord
import random

class class_choice_select(discord.ui.Select):
    plugin=None
    async def callback(self, interaction: discord.Interaction):
        if await self.plugin.check_character_existing(interaction.user.id):
            await interaction.response.send_message("You have already created a character",ephemeral=True)
            return

        data = load_json()
        if "open_creation_prompts" in data:
            if str(interaction.user.id) in data["open_creation_prompts"]:
                name = data["open_creation_prompts"][str(interaction.user.id)]
                del data["open_creation_prompts"][str(interaction.user.id)]
                dump_json(data)
                self.plugin.db_cur.execute(f"INSERT INTO character VALUES (%s,1,%s,0,%s)",(str(interaction.user.id),name,int(interaction.data['values'][0])))
                self.plugin.db.commit()
                weird_announcements=["They are still young, but will conquer the world sooner or later.","Keep an eye on them or they will throw you from your throne.", "Wish them luck in these harsh lands"]
                await interaction.response.send_message(f"Behold the all mighty {name}! "+weird_announcements[random.randint(0,len(weird_announcements)-1)])
        else:
            await interaction.response.send_message("Something went wrong. Maybe refer to an admin if it happens again.")

class class_choice_view(discord.ui.View):
    character_class = class_choice_select(placeholder="your class")

    #async def on_submit(self,ctx:discord.Interaction):
    #    ctx.response.send_message(f"You created your user! You are now known as {name}",ephemeral=True)


# this might be usefull to implement
class player_combat_instance:
    current_health:float
    current_mana:float
    
    def load_from_dict(dict):
        pass

class attack:

    def __init__(self):
        self.id:int = -1
        self.name:str = ""
        self.description:str
        self.damage:float
        self.is_piercing:bool = True
        self.can_crit:bool = True
        self.physical_damage={} # [(Statname,multiplier)]
        self.magic_damage={}
        self.mana_cost:int=0

    def load_from_dict(self,data:dict):
        if "name" in data:
            self.name=data["name"]
        if "description" in data:
            self.description=data["description"]
        if "can_pierce" in data:
            self.is_piercing=bool(data["can_pierce"])
        if "can_crit" in data:
            self.can_crit=bool(data["can_crit"])
        if "physical_damage" in data:
            self.physical_damage=data["physical_damage"].copy()
        if "magic_damage" in data:
            self.magic_damage=data["magic_damage"].copy()
    
    def load_from_db(self,cur):
        if self.name=="" and self.id==-1:
            print("name nor id is set on attack object; make sure to set name or id before calling load_from_db")
            return
        if self.name!="":
            cur.execute(f"SELECT attack_id, description, can_crit, can_pierce, mana_cost FROM public.attack WHERE name='{self.name}'")
            if cur.rowcount!=1:
                print(f"The attack name {self.name} is not unique or does not exist, try harder.")
                return
        else:
            cur.execute(f"SELECT name, description, can_crit, can_pierce, mana_cost FROM public.attack WHERE attack_id=%s",(self.id,))
            if cur.rowcount!=1:
                print(f"The attack id {self.id} is not unique or does not exist, try harder.")
                return
        res=cur.fetchone()
        if self.name!="":
            self.id=res[0]
        else:
            self.name=res[0]
        res=res[1:]
        self.description=res[0]
        self.is_piercing=res[2]
        self.can_crit=res[1]
        self.mana_cost=res[3]
        cur.execute("""SELECT s.stat_name, asw.damage_type, asw.factor
                    FROM public.attack a
                    NATURAL JOIN attack_scales_with asw
                    NATURAL JOIN stats s WHERE a.name=%s;""",(self.name,))
        res=cur.fetchall()
        for i in res:
            if i[1]==0:
                self.physical_damage[i[0]]=i[2]
            if i[1]==1:
                self.magic_damage[i[0]]=i[2]

class player_class:
    def __init__(self):
        self.id:int = -1
        self.player_class:int
        self.name:str
        self.level:int
        self.level_progress:int
        self.location:int

    def load_from_db(self,cur,user_id):
        cur.execute(f"SELECT u.user_id,u.class,u.user_name,u.user_level,u.user_level_progression,u.located FROM character u WHERE u.user_id={user_id}")
        if cur.rowcount!=1:
            self.id=-1
            return
        res = cur.fetchone()
        self.id=res[0]
        self.player_class=res[1]
        self.name=res[2]
        self.level=res[3]
        self.level_progress=res[4]
        self.location=res[5]