#!usr/bin/env python3

import os
from dotenv import load_dotenv
from discord.ext import commands
from readerwriterlock import rwlock

#setup for the content warning files: read/write locks for each one and a default file in case things go wrong
_CW_FILE_LOCKS = {}
_DEFAULT_CW_FILE = "HARD WARNINGS (books containing this content should not be nominated)\n(none yet)\n\nSOFT WARNINGS (books containing this content must be flagged)\n(none yet)"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
	#ensure the appropriate data exists for each guild
	for guild in bot.guilds:
		#add rwlock for the cw file
		if guild.id not in _CW_FILE_LOCKS:
			_CW_FILE_LOCKS[guild.id] = rwlock.RWLockWrite()
		#add cwfile
		guild_cwfilename = f'{guild.name}{guild.id}.cw'
		try:
			with _CW_FILE_LOCKS[guild.id].gen_rlock():
				with open(guild_cwfilename):
					print(f'{guild_cwfilename} exists.')
		except:
			with open(guild_cwfilename, 'w') as cwfile:
				cwfile.write(_DEFAULT_CW_FILE)
			print(f'{guild_cwfilename} has been created.')
	print(f'{bot.user} has connected to Discord!')

@bot.command(name='cw')
async def content_warning(ctx):
	msg = display_cw(ctx)
	await ctx.send(msg)


def add_cw(ctx):
	pass

def display_cw(ctx):
	#find appropriate guild(s)
	if ctx.guild:
		guilds = [ctx.guild]
	else:
		guilds = ctx.bot.guilds

	msg = ""
	for guild in guilds:
		if ctx.author in guild.members:
			with _CW_FILE_LOCKS[guild.id].gen_rlock():
				try:
					with open(f'{guild.name}{guild.id}.cw') as cwfile:
						msg += f'Content warnings for {guild.name}:\n'
						msg += cwfile.read()
				except:
					msg += f'No content warnings found for {guild.name}.'
	return msg








bot.run(TOKEN)