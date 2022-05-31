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
            print(f"Adding {guild.id} - {introChannel}, {generalChannel}")
            self.addGuild(guild.id, introChannel, generalChannel)
            return True
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

    prompt += f"\nName: {username}\nIntroduction: {introduction}\nNickname:"
    with open('./lastPrompt.txt', 'w') as file:
        file.write(prompt)

    TEMPERATURE = float(os.getenv('TEMPERATURE'))
    K_VAL = int(os.getenv('K'))
    P_VAL = float(os.getenv('P'))
    print(f"Temperature: {TEMPERATURE}, p: {P_VAL}, k: {K_VAL}")

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

async def getNickname(username, introduction, avatar):
    # I do not want the bot to use anyone's gender identity to nickname them, so it is filtered out here.
    originalIntro = introduction
    pattern = r'\w+\/\w+'
    introduction = re.sub(pattern, '', introduction)
    introduction = introduction.replace("pronouns", "")

    while (True):
        nickname = await predictNickname(username, introduction)

        if nickname == "" or nickname.isspace():
            print("skipping empty nickname")
            continue

        for word in bannedWords:
            if word in nickname.lower():
                print("Reject nickname for profanity")
                continue

        # Clean up the response
        nickname = nickname.split("\n")[0]
        try:
            if nickname[0] == " ":
                nickname = nickname[1:]
        except:
            print("skipping empty nickname")
            continue


        MAX_SIMILARITY = float(os.getenv('MAX_SIMILARITY'))
        MAX_WORDS = int(os.getenv('MAX_WORDS'))
        MIN_CHARS = int(os.getenv('MIN_CHARS'))

        similarity = similar(nickname, username)

        if not (similarity > MAX_SIMILARITY or len(nickname.split(" ")) > MAX_WORDS or len(nickname) < MIN_CHARS):
            if similarity <=  MAX_SIMILARITY:
                print(f"Similiarity is [{similarity}]")
                if "name is " in introduction.lower():
                    realName = introduction.lower().split("name is ")[1].split(" ")[0]
                    realName = realName.replace(",","")

                    realSimilarity = similar(realName, nickname.lower())

                    if realSimilarity <= 0.9:
                        print(f"Accepted nickname: {nickname}")
                        break
                    else:
                        print(f"Rejected nickname: {nickname}")
                else:
                    print(f"Accepted nickname: {nickname}")
                    break
        else:
            print(f"Rejected nickname: {nickname}")

    percentage = "{0:.0%}".format(similarity)

    embed=discord.Embed(title=f"Hi {username}, Welcome to the server!", color=0x21edff, description=f"Thank you for posting an introduction. I'm a bot that generates nicknames, based on what you wrote, I think the nickname **{nickname}** fits you best!")
    embed.set_author(name=f"{username} has posted an introduction", icon_url=avatar)
    embed.add_field(name=f"About {username}", value=originalIntro, inline=False)
    
    return embed

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

def getInfo(message):
    username = message.author.name
    introduction = message.content

    if introduction.startswith("-u "):
        startIndex = introduction.index('-u ')+3
        endIndex = introduction.index('-i ')-1
        username = introduction[startIndex:endIndex]
        introduction = introduction[endIndex+1:]

    if introduction.startswith("-i "):
        startIndex = introduction.index(" ")+1
        introduction = introduction[startIndex:]

    avatar = message.author.avatar_url

    return(username, introduction, avatar)

@client.event
async def on_message(message):

    # Check if the guild is known, and if not, don't run on it
    guildData = guildManager.getGuild(message.guild.id)
    if guildData == None:
        return

    # If the bot sent the message, never run on it
    if message.author == client.user:
        return
    # Check if it's in the guild's intro channel, if it isn't, don't run.
    if message.channel.id != guildData["introChannel"]:
        return

    genChannel = None
    for channel in message.guild.channels:
        if channel.id == guildData["generalChannel"]:
            genChannel = channel
    
    # If the general channel wasn't found, there's an issue.
    if genChannel == None:
        return

    async with genChannel.typing():
        result = getInfo(message)

        username = result[0]
        introduction = result[1]
        avatar = result[2]

        print(f"Finding nickname for {username}")
        embed = await getNickname(username, introduction, avatar)

    sentMessage = await genChannel.send(embed=embed)

    
client.run(DISCORD_KEY)