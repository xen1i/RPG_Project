## Introduction

Hi! Welcome to our little project, which combines a postgres database and discord bot to create a small RPG game.
You can have a look around and read through all sorts of functions if you want to. If you want to run the bot yourself head to the [Set up](#set-up) section

## Set up

### Requirements

First things first. If you want to run this project, you are gonna need some things.
- have a Postgres Server running on any machine
- have the token of a Discord Bot 

If you have these things set up, we can start!  You are gonna need a dedicated database on you Postgres Server, best make a new one. Then you need to use the template.sql file to create all tables and views needed for the bot. You can use the following command for that:

```
psql -U your_user -d your_database -f template.sql
```

When you have that set up, you proceed by following the steps in the template.ini file (setup the database access). \

That completes all the steps around the database. Now you can integrate your discord api token. To do that, create a file called "token.txt" in the datafiles folder and paste your api token into the file.

After completing that step you only have to install the python modules listed in requirements.txt. \
Depending on your system, you might use

```
pip install -r setupfiles/requirements.txt
```
to install the dependencies. 

Finally you can launch the main.py file with python3 and your bot should come online and work like ours (excluding the user data).