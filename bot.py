#!usr/bin/env python3

import os
from dotenv import load_dotenv
from discord.ext import commands
from readerwriterlock import rwlock

#setup for the content warning files: read/write locks for each one and a default file in case things go wrong
_CW_FILE_LOCKS = {}

#takes a cwfile and reads it into lists
#assumes the caller has locked the resource appropriately
def load_cwfile(cwfile):
	print(f'loading {cwfile.name}...')
	bans = []
	warnings = []
	flag = False
	for line in cwfile:
		if line.strip() == "**BANS**": 
			flag = True
		elif line.strip() == "**WARNINGS**": 
			flag = False
		elif line.strip() == "":
			continue
		else:
			if flag:
				bans.append(line.strip().lower())
			else:
				warnings.append(line.strip().lower())
	print(f'{cwfile.name} loaded.')
	return bans, warnings

#takes a cwfile and writes back to it
#assumes the caller has locked the resource appropriately
def store_cwfile(cwfile, bans, warnings):
	print(f'updating {cwfile.name}...')
	cwfile.write("**BANS**\n")
	cwfile.write("\n".join(bans))
	cwfile.write("\n**WARNINGS**\n")
	cwfile.write("\n".join(warnings))
	print(f'{cwfile.name} updated.')


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
				store_cwfile(cwfile, [], [])
			print(f'{guild_cwfilename} has been created.')
	print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_member_join(member):
	await member.create_dm()
	await member.dm_channel.send(

		f'Hi {member.name}, welcome to {member.guild.name}! My name is Bookerton. You can message me for help with book nominations, content warnings, and various other things. For a list of my commands message `!help` here in our chat! If I seem to be broken, please notify @SardonicDragon or @colopop.'

	)

@bot.command(name='list-cw', help='Lists the content warnings for the club.', category='Content Warnings')
async def list_cw(ctx):
	#find appropriate guild(s)
	if ctx.guild:
		guilds = [ctx.guild]
	else:
		guilds = ctx.bot.guilds

	msg = ""
	for guild in guilds:
		#display the info for every server where the author is a member
		if ctx.author in guild.members:
			with _CW_FILE_LOCKS[guild.id].gen_rlock():
				try:
					#if the file exists, print it out (formatted)
					with open(f'{guild.name}{guild.id}.cw') as cwfile:
						msg += f'Content warnings for {guild.name}:\n'
						bans, warnings = load_cwfile(cwfile)
						#print the bans
						msg += ">>> **BANS** _(Books containing this content should not be nominated.)_\n"
						if len(bans) == 0:
							msg += "(none yet)\n"
						else:
							msg += "\n".join(bans)
						msg += "\n"
						#print the warnings
						msg += "**WARNINGS** _(Books containing this content must be flagged)._\n"
						if len(warnings) == 0:
							msg += "(none yet)\n"
						else:
							msg += "\n".join(warnings)
				except:
					#the file doesn't exist somehow
					msg += f'No content warnings found for {guild.name}.'
	await ctx.send(msg)

@bot.command(name='add-cw', help="Adds a type of content to ban (with -ban) or flag (with -warn).", category="Content Warnings")
async def add_cw(ctx, level=None, warning=None):
	if None == warning or ('-ban' != level.lower() and '-warn' != level.lower()):
		await ctx.send(f'Usage: `!add-cw warning_level "content_type"`\n"warning_level" can be `-ban` or `-warn` \nExample: !add-cw -warn "the dog dies"')
		return

	#find appropriate guild(s)
	if ctx.guild:
		guilds = [ctx.guild]
	else:
		guilds = ctx.bot.guilds

	msg = ""
	for guild in guilds:
		if ctx.author in guild.members:
			msg += f'{guild.name}: '
			with _CW_FILE_LOCKS[guild.id].gen_wlock():
				with open(f'{guild.name}{guild.id}.cw', 'r+') as cwfile:
					bans, warnings = load_cwfile(cwfile)
					#first check if the warning is already there
					if warning.lower() in bans:
						msg += f'ban for {warning} already exists.\n'
						continue
					elif warning.lower() in warnings:
						if '-s' == level.lower():
							msg += f'warning for {warning} already exists.\n'
							continue
						else:
							bans.append(warning.lower())
							warnings.remove(warning.lower())
							msg += f'upgraded {warning} from warning to ban.\n'
					else:
						#add the warning to the appropriate section
						if '-ban' == level.lower():
							bans.append(warning.lower())
							msg += f'added ban on {warning}'
						elif '-warn' == level.lower():
							warnings.append(warning.lower())
							msg += f'added warning for {warning}'

					#write back to the file
					cwfile.seek(0)
					store_cwfile(cwfile, bans, warnings)


	await ctx.send(msg)
	


bot.run(TOKEN)