import os
import random
import string
from difflib import SequenceMatcher
import os.path
import cohere
import discord
from dotenv import load_dotenv

load_dotenv()
COHERE_KEY = os.getenv('COHERE_KEY')
DISCORD_KEY = os.getenv('DISCORD_KEY')

SERVER = int(os.getenv('SERVER'))
INTRO_CHANNEL = int(os.getenv('INTRO_CHANNEL'))
OUTPUT_CHANNEL = int(os.getenv('OUTPUT_CHANNEL'))

client = discord.Client()
co = cohere.Client(COHERE_KEY)

introMessage = None
sentMessage = None

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

    prediction = co.generate(
        model='large',
        prompt=(prompt),
        max_tokens=50,
        temperature=0.75,
        stop_sequences=["--"],
        k=0,
        p=0.75)
    response = ' {}'.format(prediction.generations[0].text)[1:]
    return response

async def getNickname(username, introduction, avatar):
    while (True):
        nickname = await predictNickname(username, introduction)

        if nickname == "" or nickname.isspace():
            print("skipping empty nickname")
            continue

        # Clean up the response
        nickname = nickname.split("\n")[0]
        if nickname[0] == " ":
            nickname = nickname[1:]

        MAX_SIMILARITY = float(os.getenv('MAX_SIMILARITY'))
        MAX_WORDS = int(os.getenv('MAX_WORDS'))
        MIN_CHARS = int(os.getenv('MIN_CHARS'))

        similarity = similar(nickname, username)

        if not (similarity > MAX_SIMILARITY or len(nickname.split(" ")) > MAX_WORDS or len(nickname) < MIN_CHARS):
            print(f"Accepted nickname: {nickname}")
            if similarity <=  MAX_SIMILARITY:
                print(f"Similiarity is [{similarity}]")
            break
        else:
            print(f"Rejected nickname: {nickname}")

    embed=discord.Embed(title=f"I hereby nickname them... {nickname}", color=0x21edff, description="Please let Libra know if this nickname is inappropriate!")
    embed.set_author(name=f"{username} has posted an introduction!", icon_url=avatar)
    return embed

def getInfo(message):
    username = message.author.name
    introduction = message.content

    if introduction.startswith("-u "):
        startIndex = introduction.index('-u ')+3
        endIndex = introduction.index('-i ')
        username = introduction[startIndex:endIndex]
        introduction = introduction[endIndex:]

    if introduction.startswith("-i "):
        startIndex = introduction.index(" ")+1
        introduction = introduction[startIndex:]

    avatar = message.author.avatar_url

    return(username, introduction, avatar)

@client.event
async def on_ready():
    print("logged in!")

@client.event
async def on_message(message):
    global introMessage
    global sentMessage

    # Check to see if we should even run code on it
    if message.author == client.user:
        return
    elif message.channel.id != INTRO_CHANNEL:
        if not (message.channel.id == OUTPUT_CHANNEL and (message.content.startswith("-u ") or message.content.startswith("-i "))):
            return

    if sentMessage != None:
        await sentMessage.clear_reactions()
    introMessage = message

    guild = client.get_guild(SERVER)
    channel = guild.get_channel(OUTPUT_CHANNEL)

    async with channel.typing():
        result = getInfo(message)

        username = result[0]
        introduction = result[1]
        avatar = result[2]

        print(f"Finding nickname for {username}")
        embed = await getNickname(username, introduction, avatar)

    sentMessage = await channel.send(embed=embed)
    await sentMessage.add_reaction("🔄")

@client.event
async def on_raw_reaction_add(react_obj):
    global introMessage
    global sentMessage

    if client.user == react_obj.member:
        return
    if not (react_obj.channel_id in [INTRO_CHANNEL, OUTPUT_CHANNEL]):
        return

    channel = client.get_channel(react_obj.channel_id)
    message = await channel.fetch_message(react_obj.message_id)

    if str(react_obj.emoji) == "❌":
            await message.delete()
            return

    if message == sentMessage:
        if str(react_obj.emoji) == "🔄":
            await sentMessage.clear_reactions()
            embed=discord.Embed(title=f"Rerolling...", color=0x21edff)
            await sentMessage.edit(embed=embed)

            result = getInfo(introMessage)

            username = result[0]
            introduction = result[1]
            avatar = result[2]

            print(f"Finding nickname for {username}")
            embed = await getNickname(username, introduction, avatar)

            await sentMessage.add_reaction("🔄")
            await sentMessage.edit(embed=embed)
    
client.run(DISCORD_KEY)