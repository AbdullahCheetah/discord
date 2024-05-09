import os
import discord
from openai import OpenAI
from keep_alive import keep_alive
from chatbot import ai_responses
from mongodb import add_user, get_user 
from subtitles import get_subtitles
TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_KEY = os.getenv('OPENAI_KEY')

intents = discord.Intents.all()

# Create a single client instance for both script writing and video processing
client = discord.Client(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    print("Received message:", message.content)

    # Only respond to messages from other users, not from the bot itself
    if message.author == client.user:
        return
    member_id = str(message.author.id)

# Check if the user exists in the database, if not, add them
    user = get_user(member_id)
    if not user:
        user_data = {
            "_id": member_id,
            "name": message.author.name,
            # Add any other relevant user info here
        }
        add_user(user_data)

    # Check if the bot is mentioned in the message
    if client.user in message.mentions:
        # Handle script writing logic
        if message.content and not message.attachments :
            print(message)
            response = ai_responses(message.content, member_id)
            await message.channel.send(response)

        # Handle video processing logic
        if message.attachments:
            video_attachment = message.attachments[0]
            video_url = video_attachment.url
            print(video_url)

            # Specify the folder to store the uploaded videos
            upload_folder = "../videos/"

            # Create the folder if it doesn't exist
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Download and save the video to the specified folder
            video_filename = os.path.join(upload_folder, f"uploaded_video_{video_attachment.filename}")
            await video_attachment.save(video_filename)
            vid_path = get_subtitles(video_filename)
            # Add your additional processing logic here (e.g., further processing, analysis, etc.)
            await message.channel.send(f"Received video: {vid_path}. Saved as: {video_filename}")

keep_alive()

# Start the bot
client.run(TOKEN)
