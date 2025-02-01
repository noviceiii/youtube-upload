#!/usr/bin/python3

# This script uploads a video to YouTube using the YouTube Data API v3.
# It uses OAuth 2.0 for authentication and authorization.
# The script supports resumable uploads and sets video metadata such as title, description, keywords, and privacy status.

# @version 1.2.0, 2025-02-01    

import configparser
import http.client
import httplib2
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Define retriable status codes for which we'll attempt to retry the request
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Define exceptions for which we'll retry the upload
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Check if the config file exists
config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.cfg')
if not os.path.exists(config_file_path):
    sys.exit(f"Error: Configuration file '{config_file_path}' does not exist.")

# Load configuration from config.cfg
config = configparser.ConfigParser()
config.read(config_file_path)

# File paths from config.cfg
CLIENT_SECRETS_FILE = os.path.abspath(config.get('authentication', 'client_secrets_file'))
OAUTH2_STORAGE_FILE = os.path.abspath(config.get('authentication', 'oauth2_storage_file'))

# Token management from config.cfg
FORCE_TOKEN_REFRESH_DAYS = config.getint('token_management', 'force_token_refresh_days')

# Upload settings from config.cfg
MAX_RETRIES = config.getint('upload_settings', 'MAX_RETRIES')

# These OAuth 2.0 scopes allow the application to upload videos and manage YouTube channels
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Message to display if the CLIENT_SECRETS_FILE is missing
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

# Valid privacy statuses for YouTube videos
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def check_files():
    """
    Check if required files exist.
    """
    required_files = [CLIENT_SECRETS_FILE]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Error: Required file {file} does not exist.")
            sys.exit(1)

def get_authenticated_service(args):
    """
    Get an authenticated YouTube service object.

    This function checks for existing credentials, refreshes them if needed, or 
    initiates a new authentication process if no valid credentials are found.
    """
    creds = None
    if os.path.exists(OAUTH2_STORAGE_FILE):
        try:
            # Load credentials from file
            with open(OAUTH2_STORAGE_FILE, 'r') as token:
                creds_data = token.read()
            creds = Credentials.from_authorized_user_info(json.loads(creds_data), SCOPES)
            print(f"Existing credentials loaded: {creds}")
            
            # Token Refresh Logic
            current_time = datetime.now()
            expiry_str = creds.expiry.isoformat()

            # Ensure expiry string includes microseconds
            if '.' not in expiry_str:
                expiry_str += '.000000'

            expiry = datetime.strptime(expiry_str, "%Y-%m-%dT%H:%M:%S.%f")
            
            # Check if token should be refreshed
            should_refresh = (current_time > expiry) or \
                             (current_time - expiry).days >= FORCE_TOKEN_REFRESH_DAYS or \
                             args.force_refresh

            if should_refresh:
                print("Token refresh is triggered.")
                try:
                    creds.refresh(Request())
                    print("Token refreshed: ", creds)
                    # Here we explicitly update the credentials with refreshed values
                    creds = Credentials(
                        token=creds.token,
                        refresh_token=creds.refresh_token,
                        token_uri=creds.token_uri,
                        client_id=creds.client_id,
                        client_secret=creds.client_secret,
                        scopes=creds.scopes,
                        expiry=creds.expiry
                    )
                    with open(OAUTH2_STORAGE_FILE, 'w') as token:
                        token.write(creds.to_json())
                        print(f"Updated credentials saved to {OAUTH2_STORAGE_FILE}")
                except Exception as e:
                    print(f"Failed to refresh token: {e}. Initiating new authentication.")
                    os.remove(OAUTH2_STORAGE_FILE)
                    creds = None  # Reset credentials to force new authentication
        except ValueError as ve:
            print(f"The credentials file is invalid or corrupted ({ve}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
        
        # Set up the authorization URL with offline access and incremental authorization
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        if args.nolocalauth or not creds:  # Use manual auth if nolocalauth is set or no credentials exist
            print("Manual authentication required.")
            print(f"Please visit this URL to authorize the application: {authorization_url}")
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
                print(f"Please visit this URL to authorize the application: {authorization_url}")
                code = input("Enter the authorization code: ")
                print(f"Code entered: {code}")
                flow.fetch_token(code=code)
                creds = flow.credentials  # Get the actual credentials object
                print(f"Credentials after manual auth: {creds}")

        # Save the credentials for the next run
        with open(OAUTH2_STORAGE_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Credentials saved to {OAUTH2_STORAGE_FILE}")

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def initialize_upload(youtube, options):
    """
    Initialize and execute the upload process for a video to YouTube.

    This function prepares the video metadata and initiates the upload.
    """
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
    
    # If a thumbnail was specified
    if options.thumbnail:
        upload_thumbnail(youtube, response['id'], options.thumbnail)
    
    # If a playlist ID was provided, add the video to the playlist
    if options.playlistId:
        add_video_to_playlist(youtube, response['id'], options.playlistId)

def add_video_to_playlist(youtube, video_id, playlist_id):
    """
    Add the uploaded video to a specified playlist.
    """
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
    """
    Upload a thumbnail for the video if specified.
    """
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        response = request.execute()
        print(f"Thumbnail uploaded for video {video_id}: {response}")
    except HttpError as e:
        print(f"An error occurred while uploading the thumbnail: {e}")

def resumable_upload(insert_request):
    """
    Implement resumable upload with exponential backoff strategy for failed uploads.
    """
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

    # Main parser for video upload parameters
    parser = argparse.ArgumentParser()
    parser.add_argument("--videofile", help="Video file to upload")
    parser.add_argument("--title", help="Video title", default="Test Title")
    parser.add_argument("--description", help="Video description", default="Test Description")
    parser.add_argument("--category", default="22", help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    parser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES, default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
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
    parser.add_argument("--defaultAudioLanguage", help="Default audio language for the video, e.g., 'de-CH'")
    
    # Separate group for non youtube related parameters
    auth_group = parser.add_argument_group('Authentication or debugging related options')
    auth_group.add_argument("--no-upload", action="store_true", help="Only authenticate, do not upload the video")
    auth_group.add_argument("--nolocalauth", action="store_true", help="Do not use local browser for authentication")
    auth_group.add_argument("--force-refresh", action="store_true", help="Force token refresh. Useful for debugging together with --no-upload")

    args = parser.parse_args()

    # Check if videofile is required only when not using --no-upload
    if not args.no_upload and not args.videofile:
        sys.exit("Please specify a valid file using the --videofile= parameter if not using --no-upload. Use --help for more information.")

    check_files()

    youtube = get_authenticated_service(args)
    try:
        if not args.no_upload:
            initialize_upload(youtube, args)
        else:
            print("Authentication completed. No video uploaded.")
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")