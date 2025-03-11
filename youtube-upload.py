#!/usr/bin/python3

# This script uploads a video to YouTube using the YouTube Data API v3.
# It uses OAuth 2.0 for authentication and authorization, adapted for headless systems.
# The script supports resumable uploads and sets video metadata such as title, description, keywords, and privacy status.

# @version 1.2.1, 2025-03-11

import configparser
import http.client
import httplib2
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone  # Use timezone.utc instead of UTC

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

httplib2.RETRIES = 1
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.cfg')
if not os.path.exists(config_file_path):
    sys.exit(f"Error: Configuration file '{config_file_path}' does not exist.")

config = configparser.ConfigParser()
config.read(config_file_path)

CLIENT_SECRETS_FILE = os.path.abspath(config.get('authentication', 'client_secrets_file'))
OAUTH2_STORAGE_FILE = os.path.abspath(config.get('authentication', 'oauth2_storage_file'))
FORCE_TOKEN_REFRESH_DAYS = config.getint('token_management', 'force_token_refresh_days')
MAX_RETRIES = config.getint('upload_settings', 'MAX_RETRIES')

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__), CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def check_files():
    """Check if required files exist."""
    required_files = [CLIENT_SECRETS_FILE]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Error: Required file {file} does not exist.")
            sys.exit(1)

def refresh_token_with_retry(creds):
    """Attempt to refresh the token with retries."""
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        try:
            creds.refresh(Request())
            print(f"Refresh successful: new expiry={creds.expiry}")
            return True
        except HttpError as e:
            print(f"HttpError refreshing token (attempt {retry_count+1}): status={e.resp.status}, content={e.content}")
        except RefreshError as e:
            print(f"RefreshError refreshing token (attempt {retry_count+1}): {e}")
        except Exception as e:
            print(f"Unexpected error refreshing token (attempt {retry_count+1}): {e}")
        retry_count += 1
        time.sleep(2 ** retry_count)
    return False

def get_authenticated_service(args):
    """
    Get an authenticated YouTube service object for headless systems.

    Ensures correct handling of token expiry for automatic refresh.
    Keeps creds.expiry offset-naive for library compatibility, uses custom expiry check with timezone-aware current_time.
    Compatible with Python 3.9+ using timezone.utc.
    """
    creds = None
    
    if os.path.exists(OAUTH2_STORAGE_FILE):
        try:
            with open(OAUTH2_STORAGE_FILE, 'r') as token:
                creds_data = json.load(token)
            print(f"Loaded credentials data: {creds_data}")
            creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
            print(f"Existing credentials: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10]}...")
            
            current_time = datetime.now(timezone.utc)  # Timezone-aware UTC
            should_refresh = False
            
            if not creds.refresh_token:
                print("No refresh token available, forcing new authentication.")
                should_refresh = True
            elif creds.expiry:
                # Do not modify creds.expiry to keep it offset-naive for library compatibility
                # Convert to timezone-aware for our comparison
                expiry_aware = creds.expiry.replace(tzinfo=timezone.utc)
                time_to_expiry = expiry_aware - current_time
                print(f"Token expiry: {creds.expiry}, time to expiry: {time_to_expiry}")
                # Custom expiry check
                is_expired = current_time >= expiry_aware
                should_refresh = (is_expired or 
                                  time_to_expiry.total_seconds() < 300 or  # Refresh if less than 5 minutes remaining
                                  time_to_expiry.days <= -FORCE_TOKEN_REFRESH_DAYS or
                                  args.force_refresh)
            else:
                print("No expiry set in credentials, forcing refresh.")
                should_refresh = True

            if should_refresh and creds and creds.refresh_token:
                print("Attempting to refresh token.")
                success = refresh_token_with_retry(creds)
                if success:
                    print(f"Token refreshed: token={creds.token[:10]}..., expiry={creds.expiry}")
                    with open(OAUTH2_STORAGE_FILE, 'w') as token:
                        json.dump(json.loads(creds.to_json()), token)
                        print(f"Updated credentials saved to {OAUTH2_STORAGE_FILE}")
                else:
                    print("Token refresh failed after retries, forcing new authentication.")
                    os.remove(OAUTH2_STORAGE_FILE)
                    creds = None
                    
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Invalid or corrupted credentials file ({e}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE)
            creds = None

    if not creds or not creds.valid:
        print("No valid credentials found, initiating manual authentication for headless system.")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        print(f"Please visit this URL on a device with a browser to authorize the application:")
        print(authorization_url)
        code = input("Enter the authorization code: ").strip()
        print(f"Code entered: {code}")
        
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            print(f"Credentials obtained: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10]}...")
            if not creds.expiry:
                print("Warning: No expiry set after initial authentication, setting manually.")
                creds.expiry = datetime.utcnow() + timedelta(seconds=3600)  # Keep offset-naive for library
        except Exception as e:
            print(f"Failed to fetch token with code: {e}")
            sys.exit(1)

        with open(OAUTH2_STORAGE_FILE, 'w') as token:
            json.dump(json.loads(creds.to_json()), token)
            print(f"Credentials saved to {OAUTH2_STORAGE_FILE}, expiry={creds.expiry}")

    if creds and not creds.valid and creds.refresh_token:
        print("Credentials invalid but refresh token available, attempting final refresh.")
        success = refresh_token_with_retry(creds)
        if success:
            with open(OAUTH2_STORAGE_FILE, 'w') as token:
                json.dump(json.loads(creds.to_json()), token)
            print(f"Credentials refreshed: token={creds.token[:10]}..., expiry={creds.expiry}")
        else:
            print("Final refresh attempt failed. Please re-authenticate manually.")
            os.remove(OAUTH2_STORAGE_FILE)
            sys.exit(1)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

def initialize_upload(youtube, options):
    """Initialize and execute the upload process for a video to YouTube."""
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

    if options.ageGroup or options.gender or options.geo:
        body['status']['targeting'] = {}
        if options.ageGroup:
            body['status']['targeting']['ageGroup'] = options.ageGroup
        if options.gender:
            body['status']['targeting']['genders'] = [options.gender]
        if options.geo:
            body['status']['targeting']['countries'] = options.geo.split(',')

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.videofile, chunksize=-1, resumable=True)
    )

    response = resumable_upload(insert_request)
    
    if options.thumbnail:
        upload_thumbnail(youtube, response['id'], options.thumbnail)
    
    if options.playlistId:
        add_video_to_playlist(youtube, response['id'], options.playlistId)

def add_video_to_playlist(youtube, video_id, playlist_id):
    """Add the uploaded video to a specified playlist."""
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
    """Upload a thumbnail for the video if specified."""
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
    """Implement resumable upload with exponential backoff strategy."""
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
                    raise Exception(f"The upload failed with an unexpected response: {response}")
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

    return None

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--videofile", help="Video file to upload")
    parser.add_argument("--title", help="Video title", default="Test Title")
    parser.add_argument("--description", help="Video description", default="Test Description")
    parser.add_argument("--category", default="22", help="Numeric video category.")
    parser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    parser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES, default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    parser.add_argument("--latitude", help="Latitude of the video location", type=float)
    parser.add_argument("--longitude", help="Longitude of the video location", type=float)
    parser.add_argument("--language", help="Language of the video", default="en")
    parser.add_argument("--playlistId", help="ID of the playlist where the video should be added")
    parser.add_argument("--thumbnail", help="Path to the thumbnail image file")
    parser.add_argument("--license", choices=['youtube', 'creativeCommon'], help="License of the video", default='youtube')
    parser.add_argument("--publishAt", help="ISO 8601 timestamp for scheduling video publish time")
    parser.add_argument("--publicStatsViewable", action="store_true", help="Whether video statistics should be public", default=False)
    parser.add_argument("--madeForKids", action="store_true", help="Set if the video is made for kids", default=False)
    parser.add_argument("--ageGroup", help="Age group for the video (e.g., 'age18_24')")
    parser.add_argument("--gender", help="Gender targeting for the video ('male', 'female')")
    parser.add_argument("--geo", help="Geographic targeting (comma-separated ISO 3166-1 alpha-2 country codes)")
    parser.add_argument("--defaultAudioLanguage", help="Default audio language for the video")
    
    auth_group = parser.add_argument_group('Authentication or debugging related options')
    auth_group.add_argument("--no-upload", action="store_true", help="Only authenticate, do not upload the video")
    auth_group.add_argument("--force-refresh", action="store_true", help="Force token refresh for debugging")

    args = parser.parse_args()

    if not args.no_upload and not args.videofile:
        sys.exit("Please specify a valid file using the --videofile= parameter if not using --no-upload.")

    check_files()

    youtube = get_authenticated_service(args)
    try:
        if not args.no_upload:
            initialize_upload(youtube, args)
        else:
            print("Authentication completed. No video uploaded.")
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")