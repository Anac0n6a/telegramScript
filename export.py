# Step 1: Import necessary libraries
from telethon import TelegramClient
from telethon import functions, types
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import json
import os
from dotenv import load_dotenv

# Step 2: Load environment variables from the .env file
load_dotenv()

# Step 3: Get environment variables
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')

# Step 4: Create the Telegram client
client = TelegramClient(
    'session_name',
    api_id,
    api_hash,
    device_model='Custom Device',
    system_version='4.16.30-vxCUSTOM',
    app_version='8.4.1',
    lang_code='en'
)


# Step 5: Define an asynchronous function to get all contacts
async def get_all_contacts():
    async with client:
        contacts = await client(functions.contacts.GetContactsRequest(hash=0))

        # Create a list to store contacts
        contacts_data = []

        for contact in contacts.users:
            # Add contact to the list
            contacts_data.append({
                'id': contact.id,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'username': contact.username,
                'phone': contact.phone
            })

        return contacts_data


# Step 6: Define an asynchronous function to export chat messages
async def export_chat(chat_id, contact_name):
    async with client:
        # Get all messages from the chat
        messages = await client.get_messages(chat_id, limit=None)
        
        # Create a list to store messages
        chat_data = []
        
        # Folder to store messages and media files
        contact_folder = os.path.join(os.getcwd(), contact_name)
        media_folder = os.path.join(contact_folder, 'media')
        os.makedirs(media_folder, exist_ok=True)

        for message in messages:
            message_data = {
                'id': message.id,
                'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                'sender_id': message.sender_id,
                'message': message.message
            }

            # Check for media files in the message
            if message.media:
                media_path = await client.download_media(message, media_folder)
                message_data['media'] = media_path

            # Add message to the list
            chat_data.append(message_data)

        # Save messages to a JSON file
        file_name = os.path.join(contact_folder, 'chat_export.json')
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=4)

        return contact_folder


# Step 7: Define a function to upload folders to Google Drive
def upload_to_drive(folder_path, drive, parent_folder_id=None):
    # Create a folder for the contact on Google Drive
    folder_name = os.path.basename(folder_path)
    gfolder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_folder_id}] if parent_folder_id else []
    })
    gfolder.Upload()
    folder_id = gfolder['id']

    # Create a media folder inside the contact folder on Google Drive
    media_folder = drive.CreateFile({
        'title': 'media',
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': folder_id}]
    })
    media_folder.Upload()
    media_folder_id = media_folder['id']

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Get only the file name without the path
            file_name = os.path.basename(file_path)
            # Check the file name without the path
            if file_name == 'chat_export.json':
                destination_folder_id = folder_id
            else:
                destination_folder_id = media_folder_id
            gfile = drive.CreateFile({'parents': [{'id': destination_folder_id}]})
            gfile.SetContentFile(file_path)
            gfile['title'] = file_name  # Set a simple file name without the path
            gfile.Upload()
            print(f'Uploaded {file_name} to Google Drive.')


# Step 8: Define the main asynchronous function to orchestrate the process
async def main():
    await client.start(phone_number)

    # Authenticate to Google Drive
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    # Get all contacts
    contacts = await get_all_contacts()

    for contact in contacts:
        # Determine the chat ID or username
        chat_id = contact['id']
        contact_name = f"{contact['first_name']}_{contact['last_name']}"

        # Export messages for each contact
        contact_folder = await export_chat(chat_id, contact_name)
        print(f'Chat for {contact_name} exported successfully!')

        # Upload folder to Google Drive
        upload_to_drive(contact_folder, drive)
        print(f'Folder for {contact_name} uploaded to Google Drive.')

    # Save contacts to a JSON file
    with open('contacts_export.json', 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=4)

    print('Contacts exported successfully!')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())