import os
import random
import string
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

async def predictNickname(username, introduction):

    if os.path.exists('./nicknamePrompt.txt'):
        with open('./nicknamePrompt.txt', 'r') as file:
            prompt = file.read()
            file.close()
    else:
        raise ValueError("./nicknamePrompt.txt does not exist.")

    prompt += f"\nName: {username}\nIntroduction: {introduction}\nNickname:"

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

@client.event
async def on_ready():
    print("logged in!")

@client.event
async def on_message(message):

    # Check to see if we should even run code on it
    if message.author == client.user:
        return
    elif message.channel.id != INTRO_CHANNEL:
        if not (message.channel.id == OUTPUT_CHANNEL and message.content.startswith("-t")):
            return

    guild = client.get_guild(SERVER)
    channel = guild.get_channel(OUTPUT_CHANNEL)

    async with channel.typing():
        username = message.author.name
        avatar = message.author.avatar_url
        introduction = message.content
        nickname = await predictNickname(username, introduction)

        # Clean up the response
        nickname = nickname.split("\n")[0]
        if nickname[0] == " ":
            nickname = nickname[1:]

        embed=discord.Embed(title=f"I hereby nickname them... {nickname}", color=0x21edff, description="Please let Libra know if this nickname is inappropriate!")
        embed.set_author(name=f"{username} has posted an introduction!", icon_url=avatar)

    await channel.send(embed=embed)
    
client.run(DISCORD_KEY)