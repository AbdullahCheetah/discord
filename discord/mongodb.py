from pymongo import MongoClient
import os

MONGODB_URI = os.getenv('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client.Cluster0
# Collection Definitions
users_collection = db.users
chat_history_collection = db.chat_history

# User operations
def add_user(user_data):
    return users_collection.insert_one(user_data).inserted_id

def get_user(user_id):
    return users_collection.find_one({"_id": user_id})

def update_user(user_id, update_data):
    users_collection.update_one({"_id": user_id}, {"$set": update_data})

# Chat history operations
def set_chat_history(user_id, message_data):
    """
    Creates a new chat history record or updates an existing one for a user.
    """
    chat_history_collection.update_one(
        {"user_id": user_id},
        {"$push": {"messages": {"$each": message_data}}},  # Using $each to add all elements
        upsert=True
    )

def get_chat_history(user_id):
    """
    Retrieves the chat history for a specific user.
    """
    return chat_history_collection.find_one({"user_id": user_id})

def update_chat_history(user_id, update_data):
    """
    Updates the chat history record for a specific user.
    """
    chat_history_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )