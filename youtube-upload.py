#!/usr/bin/python3

# This script uploads a video to YouTube using the YouTube Data API v3.
# It uses OAuth 2.0 for authentication and authorization.
# Usage:  python3 youtube-upload.py --videofile=VIDEO_FILE --title=VIDEO_TITLE --description=VIDEO_DESCRIPTION --category=CATEGORY_ID --keywords=KEYWORDS --privacyStatus=PRIVACY_STATUS --nolocalauth --latitude=LATITUDE --longitude=LONGITUDE --language=LANGUAGE --playlistId=PLAYLIST_ID --thumbnail=THUMBNAIL_PATH --license=LICENSE --publishAt=PUBLISH_AT --publicStatsViewable --madeForKids --ageGroup=AGE_GROUP --gender=GENDER --geo=GEO

# @version 1.0.0-pre, 2025-01-11
# 1.0.1-pre,    2025-01-12     absolute path for config file
# 1.0.2-pre,    2025-01-13     added playlistId, thumbnail, license, publishAt, publicStatsViewable, madeFor, ageGroup and childDirected parameters

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
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Check if the config file exists
config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.cfg')

if not os.path.exists(config_file_path):
    sys.exit(f"Error: Configuration file '{config_file_path}' does not exist.")

# Load configuration from config.cfg
config = configparser.ConfigParser()
config.read(config_file_path)

CLIENT_SECRETS_FILE = config.get('authentication', 'client_secrets_file')
OAUTH2_STORAGE_FILE = config.get('authentication', 'oauth2_storage_file')

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def check_files():
    # Check if required files exist
    required_files = [CLIENT_SECRETS_FILE]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Error: Required file {file} does not exist.")
            sys.exit(1)

def get_authenticated_service(args):
    creds = None
    if os.path.exists(OAUTH2_STORAGE_FILE):
        try:
            creds = Credentials.from_authorized_user_file(OAUTH2_STORAGE_FILE, SCOPES)
            print(f"Existing credentials loaded: {creds}")
        except ValueError:
            print("The credentials file is invalid or corrupted, initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("Refreshed credentials: ", creds)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
            
            if args.nolocalauth:
                print("Trying manual authentication.")
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Please visit this URL to authorize the application: {auth_url}")
                code = input("Enter the authorization code: ")
                print(f"Code entered: {code}")
                flow.fetch_token(code=code)
                creds = flow.credentials  # Get the actual credentials object
                print(f"Credentials after fetch_token: {creds}")
            else:
                # Try to use local browser, if it fails, fallback to manual authentication
                try:
                    creds = flow.run_local_server(port=0)
                    print(f"Credentials from local server: {creds}")
                except Exception as e:
                    print(f"Failed to open browser ({e}), please authorize manually:")
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"Please visit this URL to authorize the application: {auth_url}")
                    code = input("Enter the authorization code: ")
                    print(f"Code entered: {code}")
                    flow.fetch_token(code=code)
                    creds = flow.credentials  # Get the actual credentials object
                    print(f"Credentials after manual auth: {creds}")

        # Check if creds is not None before saving
        if creds:
            # Save the credentials for the next run
            with open(OAUTH2_STORAGE_FILE, 'w') as token:
                token.write(creds.to_json())
                print(f"Credentials saved to {OAUTH2_STORAGE_FILE}")
        else:
            print("Authentication failed. No credentials were received.")
            sys.exit(1)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=options.category,
            defaultLanguage=options.language,
            defaultAudioLanguage=options.defaultAudioLanguage if options.defaultAudioLanguage else None,
            recordingDetails=dict(
                location=dict(
                    latitude=float(options.latitude) if options.latitude else None,
                    longitude=float(options.longitude) if options.longitude else None
                )
            ) if options.latitude and options.longitude else None
        ),
        status=dict(
            privacyStatus=options.privacyStatus,
            selfDeclaredMadeForKids=options.madeForKids,
            license=options.license,
            publicStatsViewable=options.publicStatsViewable,
            publishAt=options.publishAt if options.publishAt else None
        )
    )

    # Adding targeting information
    if options.ageGroup or options.gender or options.geo:
        body['status']['targeting'] = {}
        if options.ageGroup:
            body['status']['targeting']['ageGroup'] = options.ageGroup
        if options.gender:
            body['status']['targeting']['genders'] = [options.gender]
        if options.geo:
            body['status']['targeting']['countries'] = options.geo.split(',')

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.videofile, chunksize=-1, resumable=True)
    )

    response = resumable_upload(insert_request)
    
    # Wenn ein Thumbnail angegeben wurde
    if options.thumbnail:
        upload_thumbnail(youtube, response['id'], options.thumbnail)
    
    # If a playlist ID was provided, add the video to the playlist
    if options.playlistId:
        add_video_to_playlist(youtube, response['id'], options.playlistId)

def add_video_to_playlist(youtube, video_id, playlist_id):
    add_video_request = youtube.playlistItems().insert(
        part="snippet",
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
    )
    response = add_video_request.execute()
    print(f"Video {video_id} added to playlist {playlist_id}")

def upload_thumbnail(youtube, video_id, thumbnail_path):
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        response = request.execute()
        print(f"Thumbnail uploaded for video {video_id}: {response}")
    except HttpError as e:
        print(f"An error occurred while uploading the thumbnail: {e}")

# This method implements an exponential backoff strategy to resume a
# failed upload.
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
                    return response
                else:
                    raise Exception("The upload failed with an unexpected response: %s" % response)
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
                sys.exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds} seconds and then retrying...")
            time.sleep(sleep_seconds)

    return None  # In case of failure

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--videofile", required=True, help="Video file to upload")
    parser.add_argument("--title", help="Video title", default="Test Title")
    parser.add_argument("--description", help="Video description", default="Test Description")
    parser.add_argument("--category", default="22", help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    parser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES, default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    parser.add_argument("--nolocalauth", action="store_true", help="Do not use local browser for authentication")
    parser.add_argument("--latitude", help="Latitude of the video location", type=float)
    parser.add_argument("--longitude", help="Longitude of the video location", type=float)
    parser.add_argument("--language", help="Language of the video", default="en")
    parser.add_argument("--playlistId", help="ID of the playlist where the video should be added")
    parser.add_argument("--thumbnail", help="Path to the thumbnail image file")
    parser.add_argument("--license", choices=['youtube', 'creativeCommon'], help="License of the video", default='youtube')
    parser.add_argument("--publishAt", help="ISO 8601 timestamp for scheduling video publish time, e.g. '2023-12-25T10:00:00Z'")
    parser.add_argument("--publicStatsViewable", action="store_true", help="Whether video statistics should be public", default=False)
    parser.add_argument("--madeForKids", action="store_true", help="Set if the video is made for kids", default=False)
    parser.add_argument("--ageGroup", help="Age group for the video (e.g., 'age18_24', 'age25_34')")
    parser.add_argument("--gender", help="Gender targeting for the video ('male', 'female')")
    parser.add_argument("--geo", help="Geographic targeting for the video (comma-separated ISO 3166-1 alpha-2 country codes, e.g., 'US,CA,UK')")
    parser.add_argument("--defaultAudioLanguage", help="Default audio language for the video, e.g., 'en-US'")

    args = parser.parse_args()

    # Check if the video file exists after parsing arguments
    if not os.path.exists(args.videofile):
        sys.exit("Please specify a valid file using the --videofile= parameter.")

    check_files()

    youtube = get_authenticated_service(args)
    try:
        initialize_upload(youtube, args)
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")