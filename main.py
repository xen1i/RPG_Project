#
# Copyright 2024 - Caspar Moritz Klein & Xenia Kukushkina
#  Mini licence: Don't distribute or modify the code, don't act like it's yours, but have fun with it alone if you wish! Also as long as the code is public, it is free to use (privately and every participant gets their own copy via the original source of distribution)
#
import discord
import discord.app_commands

import db_connect
from config import load_config

import rpg_tools

intents = discord.Intents.all()
client = discord.Client(intents=intents)
commandTree = discord.app_commands.CommandTree(client)

rpg_db_conn = None
rpg_db = None

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await setup_commandTree()

@client.event
async def on_message(message):
    print(f"logged message from {message.author}: {message.content}")
    if message.author == client.user:
        return


@client.event
async def on_member_join(member):
    print(member.name)

async def test_status(interaction:discord.Interaction):
    await interaction.response.send_message("What is it, master?",ephemeral=True)

async def setup_commandTree():
    test=discord.app_commands.Command(name="status",description="Use this command to test if the bot is running correctly",callback=test_status)
    commandTree.add_command(test)
    print("Command Tree synced succesfully!")
    await commandTree.sync()#guild=discord.Object(id=905914544063414292))

if __name__ == '__main__':
    rpg_db_conn=db_connect.connect(load_config())
    if rpg_db_conn:
        rpg_db=rpg_db_conn.cursor()

        print(rpg_db)
    else:
        print("failed connecting db")
        exit()

    rpg_tools.link(commandTree,rpg_db_conn)
    print("successfully linked "+rpg_tools.plugin_name+"!")

    with open("datafiles/token.txt","r") as tok:
        client.run(tok.readline())
