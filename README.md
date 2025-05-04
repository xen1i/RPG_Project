## Introduction

Hi! Welcome to our little project, which combines a postgres database and discord bot to create a small RPG game.
You can have a look around and read through all sorts of functions if you want to. If you want to run the bot yourself head to the [Set up](#set-up) section

## Set up

### Requirements

First things first. If you want to run this project, you are gonna need some things.
- have a Postgres Server running on any machine
- have the token of a Discord Bot ([Here's a tutorial for that](https://discordpy.readthedocs.io/en/stable/discord.html))

### Database setup
If you have these things set up, we can start!  You are gonna need a dedicated database on you Postgres Server, best make a new one. Then you need to use the template.sql file to create all tables and views needed for the bot. If the Database System runs on your local machine, you can use the following command for that:

```
psql -U your_user -d your_database -f template.sql
```
If the Database System runs on a remote machine, you can either copy the file and then run the command or adjust the command accordingly.

When you have that set up, you proceed by following the steps in the template.ini file (setup the database access).

### Discord setup

That completes all the steps around the database. Now you can integrate your discord api token. If you do not have an API token, refer to the [Requirements](#requirements). To do that, create a file called "token.txt" in the datafiles folder and paste your api token into the file.

### Finalizing

After completing that step you only have to install the python modules listed in requirements.txt. \
Depending on your system, you might use

```
pip install -r setupfiles/requirements.txt
```
to install the dependencies. 

Finally you can launch the main.py file with python3 and your bot should come online and work like ours (excluding the user data). You can then go on and edit tables to add your own: Locations, Attacks, Classes, Stats, Items or Rarities! You can even expand the schema as you like; however do not share copies of 

## License

We have put a small header into our big code files. This is meant to protect what we have created and should not restrict anyone in having fun with it or violate anyones rights. If you find that we have violated any other license by using certain dependencies and putting our mini-license on top of that, we want to apologize and anything written in the mini-license taking part in a violation loses its validity.