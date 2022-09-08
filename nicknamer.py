import os
import re
import os.path
import cohere
import discord
import json
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()
COHERE_KEY = os.getenv('COHERE_KEY')
DISCORD_KEY = os.getenv('DISCORD_KEY')

MAX_TRIES = int(os.getenv('MAX_TRIES'))
MAX_SIMILARITY = float(os.getenv('MAX_SIMILARITY'))
MAX_WORDS = int(os.getenv('MAX_WORDS'))
MIN_INTRO_WORDS = int(os.getenv('MIN_INTRO_WORDS'))
MIN_CHARS = int(os.getenv('MIN_CHARS'))

TEMPERATURE = float(os.getenv('TEMPERATURE'))
K_VAL = int(os.getenv('K'))
P_VAL = float(os.getenv('P'))

client = discord.Client()
co = cohere.Client(COHERE_KEY)

with open('./banned.json', 'r') as f:
    bannedWords = json.load(f)["bannedWords"]

class guildManagerClass():
    def __init__(self):
        self.guilds = {}

    def getGuild(self, guildId):

        if guildId in self.guilds.keys():
           return self.guilds[guildId]
        else:
            return None
        
    def addGuild(self, guildId, introChannel, generalChannel):
        guildDict = {
            "introChannel": introChannel,
            "generalChannel": generalChannel
        }

        self.guilds[guildId] = guildDict

    def registerGuild(self, guild):
        if guild.id in self.guilds.keys():
            return False

        introChannel = None
        generalChannel = None

        for channel in guild.channels:
            if "introductions" == channel.name.lower():
                if str(channel.type) == "text": introChannel = channel.id
            if "general" == channel.name.lower(): 
                if str(channel.type) == "text": generalChannel = channel.id

        if introChannel is not None and generalChannel is not None:
            print(f"Activating {guild.name}: {guild.id} - {introChannel}, {generalChannel}")
            self.addGuild(guild.id, introChannel, generalChannel)
            return True

        print(f"Failed to activate {guild.name}: {guild.id}")
        return False

guildManager = guildManagerClass()

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

async def predictNickname(username, introduction):

    if os.path.exists('./nicknamePrompt.txt'):
        with open('./nicknamePrompt.txt', 'r') as file:
            prompt = file.read()
            file.close()
    else:
        raise ValueError("./nicknamePrompt.txt does not exist.")

    introLines = introduction.splitlines()
    strippedIntro = ''.join(introLines)

    prompt += f"\nName: {username}\nIntroduction: {strippedIntro}\nNickname:"
    with open('./lastPrompt.txt', 'w') as file:
        file.write(prompt)

    print(f"temp: {TEMPERATURE}, p: {P_VAL}, k: {K_VAL}")

    prediction = co.generate(
        model='large',
        prompt=(prompt),
        max_tokens=50,
        temperature=TEMPERATURE,
        stop_sequences=["--"],
        k=K_VAL,
        p=P_VAL)
    response = ' {}'.format(prediction.generations[0].text)[1:]
    return response

async def getNickname(userId, username, introduction, avatar, casual=False, noIntro=False):

    # I do not want the bot to use anyone's gender identity to nickname them, so it is filtered out here.
    originalIntro = introduction
    pattern = r'\w+\/\w+'
    introduction = re.sub(pattern, '', introduction)
    introduction = introduction.replace("pronouns", "")

    if introduction.startswith("<@974129951907397642>"):
        introduction = introduction.replace("<@974129951907397642>","")

    tries = 0

    while (True):
        rejected = False
        
        tries += 1
        if tries > MAX_TRIES:
            return

        nickname = await predictNickname(username, introduction)

        # If the response appears empty, Reject
        if nickname == "" or nickname.isspace():
            print("[0]Rejected nickname for being empty")
            rejected = True

        # If any banned word is detected in the response, Reject
        for word in bannedWords:
            if word in nickname.lower():
                print("[1]Rejected nickname for profanity")
                rejected = True

        # Clean up the response for further processing
        nickname = nickname.split("\n")[0]
        try:
            if nickname[0] == " ":
                nickname = nickname[1:]
        except:
            print("[2]Rejected nickname for error in cleanup")
            rejected = True

        similarity = similar(nickname, username)

        # If the nickname doesn't fit the specified sizes, Reject
        if (len(nickname.split(" ")) > MAX_WORDS or len(nickname) < MIN_CHARS):
            print(f"[3]Rejected nickname: {nickname}")
            rejected = True

        # If the nickname is too similar to the username, Reject
        elif similarity > MAX_SIMILARITY:
            print(f"[4]Rejected nickname: {nickname}")
            rejected = True

        # If username is any single word in the nickname, Reject
        for word in nickname.split(" "):
            if username == word:
                print(f"[5]Rejected nickname: {nickname}")
                #rejected = True
        
        # Similarity comparisons using a detected real name
        realIdentifiers = ["name is", "go by", "am called", "call me", "i am", "i'm"]
        for identifier in realIdentifiers:
            if identifier in introduction.lower():
                realName = introduction.lower().split(identifier+" ")[1].split(" ")[0]
                realName = realName.replace(",","")

                # If realname is any single word in the nickname, Reject
                for word in nickname.split(" "):
                    if realName == word:
                        print(f"[6]Rejected nickname: {nickname}")
                        #rejected = True

                realSimilarity = similar(realName, nickname.lower())

                # If the nickname is too similar to the realname, Reject
                if realSimilarity > MAX_SIMILARITY:
                   print(f"[7]Rejected nickname: {nickname}")
                   rejected = True


        if not rejected:
            # If this point was reached, there is no issue with the name, Accept
            print(f"Accepted nickname: {nickname}")
            break
        else:
            continue
                
    percentage = "{0:.0%}".format(similarity)
    
    if len(originalIntro) > 1000:
        originalIntro = originalIntro[0:1000]+"..."

    if casual:
        embed = discord.Embed(title=f"Giving you a nickname...", color=0x21edff, description=f"<@{userId}>, I'm a bot that generates nicknames, based on what you wrote, I think the nickname **{nickname}** fits you best!")
        embed.set_author(name=f"{username} has requested a nickname", icon_url=avatar)
        embed.add_field(name=f"About {username}", value=originalIntro, inline=False)
    else:
        embed = discord.Embed(title=f"Welcome to the server!", color=0x21edff, description=f"Thank you for posting an introduction <@{userId}>. I'm a bot that generates nicknames, based on what you wrote, I think the nickname **{nickname}** fits you best!")
        embed.set_author(name=f"{username} has posted an introduction", icon_url=avatar)
        if not noIntro:
            embed.add_field(name=f"About {username}", value=originalIntro, inline=False)

    # So I can keep an eye on it
    monitorChannel = await client.fetch_channel("981050310162255942")
    await monitorChannel.send(embed=embed)

    return embed

async def runMessage(message, noIntro=False):
    # Check if the message is a system message, if so, don't run on it
    if message.is_system():
        return

    # Check if the guild is known, and if not, don't run on it
    guildData = guildManager.getGuild(message.guild.id)
    if guildData == None:
        return

    # If the bot sent the message, never run on it
    if message.author == client.user:
        return

    # Check if it's in the guild's intro channel, if it isn't, don't run.
    if message.channel.id != guildData["introChannel"] and str(message.channel.id) != "567728646668681256":
        return

    genChannel = None
    for channel in message.guild.channels:
        if channel.id == guildData["generalChannel"]:
            genChannel = channel
    
    # If the general channel wasn't found, there's an issue.
    if genChannel == None:
        return

    # See if the message is long enough to be used as an input
    if len(message.content.split(" ")) < MIN_INTRO_WORDS:
        if str(message.channel.id) != "567728646668681256":
            return

    targetChannel = genChannel

    userId = message.author.id
    username = message.author.name
    introduction =  message.content
    avatar = message.author.avatar_url

    casual = False
    if str(message.channel.id) == "567728646668681256":
        if message.content.startswith("<@974129951907397642>"):
            casual = True
            targetChannel = await client.fetch_channel("567728646668681256")
        else:
            return

    async with targetChannel.typing():
        print(f"Finding nickname for {message.author.name}")

        embed = await getNickname(userId, username, introduction, avatar, casual, noIntro=noIntro)

        if str(message.guild.id) != "481904955016478743":
            embed.add_field(name="3 rerolls remaining", value="React with 🔄 to get a new nickname", inline=False)
    
    message = await targetChannel.send(embed=embed)
    if str(message.guild.id) != "481904955016478743":
        await message.add_reaction("🔄")

@client.event
async def on_ready():
    print("Logged in!")

    for guild in client.guilds:
        guildManager.registerGuild(guild)

@client.event
async def on_guild_join(guild):
    print(f"Joined {guild}")
    
    # If the guild isn't known, add it.
    guildData = guildManager.getGuild(guild.id)
    if guildData == None:
        guildManager.registerGuild(guild)

@client.event
async def on_message(message):
    await runMessage(message)

@client.event
async def on_raw_reaction_add(react_obj):

    if react_obj.member == client.user:
        return

    channel = client.get_channel(react_obj.channel_id)
    message = await channel.fetch_message(react_obj.message_id)
    reaction = str(react_obj.emoji)

    if react_obj.member.id == 258084676994990082 and reaction == "✨":
        await runMessage(message, noIntro=True)
        return

    if str(react_obj.guild_id) == "481904955016478743" and str(react_obj.member.id) != "258084676994990082":
        return

    if message.author != client.user:
        return

    if reaction == "🔄":
        await message.clear_reactions()

        # If there's any embeds, operate on the first one.
        embeds = message.embeds
        if len(embeds) > 0:
            embed = embeds[0]
            if len(embed.fields) > 1:
                if "No rerolls remaining" in embed.fields[1].name:
                    return
                else:
                    rerollsLeft = int(embed.fields[1].name.split(" ")[0])-1
            else:
                rerollsLeft = 3

            userId = embed.author.icon_url.split("/")[4]
            user = await client.fetch_user(userId)
            introduction = embed.fields[0].value

            if userId != str(react_obj.member.id) and str(react_obj.member.id) != "258084676994990082":
                return

            userId = user.id
            username = user.name
            avatar = user.avatar_url

            embed = discord.Embed(title=f"Rerolling...", color=0x21edff)
            await message.edit(embed=embed)

            embed = await getNickname(userId, username, introduction, avatar)
            if rerollsLeft == 0:
                name="No rerolls remaining"
                value="You're stuck with this one!"
            elif rerollsLeft == 1:
                name=f"{rerollsLeft} reroll remaining"
            else:
                name=f"{rerollsLeft} rerolls remaining"
            if rerollsLeft > 0:
                value="React with 🔄 to get a new nickname"
            if str(react_obj.member.id) != "258084676994990082":
                embed.add_field(name=name, value=value, inline=False)
                if rerollsLeft != 0:
                    await message.add_reaction("🔄")
            await message.edit(embed=embed)
    
client.run(DISCORD_KEY)