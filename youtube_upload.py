#!/usr/bin/python3

import configparser
import http.client
import httplib2
import os
import random
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# Paths to the two configuration files
VIDEO_CONFIG_FILE = 'config_video.cfg'
AUTH_SETTINGS_CONFIG_FILE = 'config_auth_settings.cfg'

# Read Video config
video_config = configparser.ConfigParser()
video_config.read(VIDEO_CONFIG_FILE)

if not os.path.exists(VIDEO_CONFIG_FILE):
    raise FileNotFoundError(f"Video config file '{VIDEO_CONFIG_FILE}' not found.")

if 'Video' not in video_config:
    raise ValueError("Section [Video] is missing in video config file.")

# Read Auth/Settings config
auth_settings_config = configparser.ConfigParser()
auth_settings_config.read(AUTH_SETTINGS_CONFIG_FILE)

if not os.path.exists(AUTH_SETTINGS_CONFIG_FILE):
    raise FileNotFoundError(f"Auth/Settings config file '{AUTH_SETTINGS_CONFIG_FILE}' not found.")

required_auth = ['client_secrets_file', 'client_oauth', 'upload_scope', 'api_service_name', 'api_version']
for key in required_auth:
    if key not in auth_settings_config['Auth']:
        raise ValueError(f"Missing '{key}' in [Auth] section.")

if 'Settings' not in auth_settings_config:
    raise ValueError("Section [Settings] is missing in auth_settings config file.")
if 'max_retries' not in auth_settings_config['Settings']:
    raise ValueError("Missing 'max_retries' in [Settings] section.")

# Load values
MAX_RETRIES = int(auth_settings_config['Settings']['max_retries'])

RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine
)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

YOUTUBE_UPLOAD_SCOPE = auth_settings_config['Auth']['upload_scope']
YOUTUBE_API_SERVICE_NAME = auth_settings_config['Auth']['api_service_name']
YOUTUBE_API_VERSION = auth_settings_config['Auth']['api_version']

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    auth_settings_config['Auth']['client_secrets_file'])
)

def get_authenticated_service():
    flow = flow_from_clientsecrets(
        auth_settings_config['Auth']['client_secrets_file'],
        scope=YOUTUBE_UPLOAD_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE
    )

    STORAGE_FILE = auth_settings_config['Auth']['client_oauth']
    storage = Storage(STORAGE_FILE)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, argparser.parse_args())

    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http())
    )

def initialize_upload(youtube):
    v_cfg = video_config['Video']

    tags = None
    if v_cfg['keywords']:
        tags = v_cfg['keywords'].split(',')

    body = {
        'snippet': {
            'title': v_cfg['title'],
            'description': v_cfg['description'],
            'tags': tags,
            'categoryId': v_cfg['category']
        },
        'status': {
            'privacyStatus': v_cfg['privacyStatus']
        },
        'recordingDetails': {
            'location': {
                'latitude': float(v_cfg['latitude']),
                'longitude': float(v_cfg['longitude'])
            }
        }
    }

    insert_request = youtube.videos().insert(
        part="snippet,status,recordingDetails",
        body=body,
        media_body=MediaFileUpload(v_cfg['file'], chunksize=-1, resumable=True)
    )

    resumable_upload(insert_request)

def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print(f"Video id '{response['id']}' was successfully uploaded.")
                else:
                    exit(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds:f} seconds and then retrying...")
            time.sleep(sleep_seconds)

if __name__ == '__main__':
    youtube = get_authenticated_service()
    try:
        initialize_upload(youtube)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")