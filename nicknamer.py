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
TEST_SERVER = os.getenv('TEST_SERVER')
TEST_CHANNEL = os.getenv('TEST_CHANNEL')

client = discord.Client()
co = cohere.Client(COHERE_KEY)

lastId = 0
fakeUser = None

def predict(values, prompt):
    prediction = co.generate(
        model='medium',
        prompt=(values+prompt),
        max_tokens=100,
        temperature=0.5,
        stop_sequences=["--"],
        k=0,
        p=0.75)
    response = prompt+' {}'.format(prediction.generations[0].text)
    if "--" in response:
        response = response.split("--")[0]
    return response

def generate_user():
    users = ""
    usergen = ""
    if os.path.exists('./users.txt'):
        with open('./users.txt', 'r') as file:
            users = file.read()
            usergen = predict(users, "")
            file.close()
        return usergen
    return None

def generate_user_embed(text):
    random_color = discord.Colour.random()
    letters = string.ascii_lowercase
    random_string = ''.join(random.choice(letters) for i in range(10))
    random_avatar = f"https://avatars.dicebear.com/api/adventurer/{random_string}.png"

    embed=discord.Embed(title="Give me a nickname by replying!", description=text, color=random_color)
    embed.set_thumbnail(url=random_avatar)
    embed.add_field(name="React with ❌", value="If this user is malformed or inappropriate", inline=True)
    embed.add_field(name="React with ✅", value="If this user is indistinguishable from reality", inline=True)

    return embed

async def new_user():
    global lastId
    global fakeUser

    guild = client.get_guild(int(TEST_SERVER))
    channel = guild.get_channel(int(TEST_CHANNEL))
    
    message = await channel.send("Generating new user. Please wait...")

    fakeUser = generate_user()
    embed = generate_user_embed(fakeUser)
    
    await message.edit(content="", embed=embed)
    lastId = message.id

    await message.add_reaction(emoji="❌")
    await message.add_reaction(emoji="✅")

@client.event
async def on_ready():
    await new_user()

@client.event
async def on_raw_reaction_add(react_obj):
    if client.user == react_obj.member:
        return

    voteReacts=["❌", "✅"]

    channel = client.get_channel(react_obj.channel_id)
    message = await channel.fetch_message(react_obj.message_id)
    if str(react_obj.emoji) in voteReacts and message.author.id == client.user.id:
        if str(react_obj.emoji) == "❌":
            await message.delete()
            if message.id == lastId:
                await new_user()
        elif str(react_obj.emoji) == "✅":
            with open('./users.txt', 'a+') as file:
                if not len(file.read()+fakeUser+"--") > 2000:
                    file.write(fakeUser)
                    file.write('--')
                file.close()
    else:
        print(str(react_obj.emoji) in voteReacts)

@client.event
async def on_message(message):
    if message.reference and message.author != client.user:
        if message.reference.resolved and message.reference.message_id == lastId:
            await message.add_reaction(emoji="✅")
            with open('./nicknames.txt', 'a') as file:
                file.write(fakeUser)
                if not "\n" in fakeUser[-3:-1]:
                    file.write("\n")
                file.write("Nickname: "+message.content)
                file.write("\n--")
                file.close()
            await new_user()



client.run(DISCORD_KEY)


