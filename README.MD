# Nicknamer

## Setup

### .env File

The .env file consists of the below info, you'll need to set/adjust these

```
COHERE_KEY = [COHERE KEY HERE]
DISCORD_KEY = [DISCORD KEY HERE]

MAX_TRIES = 50
MAX_SIMILARITY = 0.8
MAX_WORDS = 4
MIN_CHARS = 5

TEMPERATURE = 0.9
K = 0
P = 0.75
```

### .JSON Files

There are a few JSON files needed to run the bot

#### nicknamePrompt.json

This file is used to preface the generated prompt, you'll need to provide about a dozen intros and some nicknames for them to get started.

```
Name: Sam
Introduction: Hey, I'm Sam! I like singing!
Nickname: SingingSam
--
Name: [NAME HERE]
Introduction: [INTRO HERE]
Nickname: [NICKNAME HERE]
```

#### banned.json

This file details words you do not want appearing in the nickname by any costs. I would recommend searching the internet for a premade list like this.

```
{
    "bannedWords": [
        "put",
        "unwanted",
        "words",
        "here"
    ]
}
```

## Invite Link
Add the bot to your server by clicking [here](https://discord.com/api/oauth2/authorize?client_id=974129951907397642&permissions=75776&scope=bot)!

## Q/A
### What is this?
Nicknamer is a small project I began to practice AI response generation.

### What's the goal?
The end goal is to produce a nickname for a Discord user based on the introduction they post when joining a server

### What does it do now?
When an introduction is sent to a server's introduction channel, it will spit out a nickname into the general channel. For this bot to work, you must have two text channels. One called "#general" and one called "#introductions" respectively. 

### Who's idea was this?
It was my friend Sierra's! She originally suggested this idea on the Good Kid Street Team Discord server.