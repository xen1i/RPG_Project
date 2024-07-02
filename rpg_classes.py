#
# Copyright 2024 - Caspar Moritz Klein & Kseniia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
from rpg_utils import load_json,dump_json,apply_scalings
import discord
import random

class class_choice_select(discord.ui.Select):
    plugin=None
    async def callback(self, interaction: discord.Interaction):
        if await self.plugin.check_character_existing(interaction.user.id):
            await interaction.response.send_message("You have already created a character",ephemeral=True)
            return

        data = load_json()
        print(str(interaction.user.id) in data["open_creation_prompts"])
        print(str(interaction.user.id))
        print(data)
        if "open_creation_prompts" in data:
            if str(interaction.user.id) in data["open_creation_prompts"]:
                name = data["open_creation_prompts"][str(interaction.user.id)]
                print(interaction.extras)
                print(interaction.data)
                print(f"INSERT INTO character VALUES ('{str(interaction.user.id)}',1,'{name}',0,{int(interaction.data['values'][0])})")
                del data["open_creation_prompts"][str(interaction.user.id)]
                dump_json(data)
                self.plugin.db_cur.execute(f"INSERT INTO character VALUES ('{str(interaction.user.id)}',1,'{name}',0,{int(interaction.data['values'][0])})")
                self.plugin.db.commit()
                weird_announcements=["They are still young, but will conquer the world sooner or later.","Keep an eye on them or they will throw you from your throne.", "Wish them luck in these harsh lands"]
                await interaction.response.send_message(f"Behold the all mighty {name}! "+weird_announcements[random.randint(0,len(weird_announcements)-1)])
        else:
            await interaction.response.send_message("Something went wrong. Maybe refer to an admin if it happens again.")

class class_choice_view(discord.ui.View):
    character_class = class_choice_select(placeholder="your class")

    #async def on_submit(self,ctx:discord.Interaction):
    #    ctx.response.send_message(f"You created your user! You are now known as {name}",ephemeral=True)

class player_combat_instance:
    current_health:float
    current_mana:float
    
    def load_from_dict(dict):
        pass

class attack:
    name:str
    description:str
    damage:float
    is_piercing:bool = True
    can_crit:bool = True
    physical_damage={} # [(Statname,multiplier)]
    magic_damage={}
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
            self.physical_damage=data["magic_damage"].copy()


