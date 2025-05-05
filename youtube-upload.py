#!/usr/bin/python3

# This script uploads a video to YouTube using the YouTube Data API v3.
# It uses OAuth 2.0 for authentication and authorization, adapted for headless systems.
# The script supports resumable uploads and sets video metadata such as title, description, keywords, and privacy status.
# Enhanced to handle automatic token refresh to prevent manual re-authentication.

# @version 1.3.0, 2025-05-05

import configparser
import http.client
import httplib2
import json
import os
import random
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import urllib.error

# Load configuration from config.cfg
config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.cfg')
if not os.path.exists(config_file_path):
    sys.exit(f"Error: Configuration file '{config_file_path}' does not exist.")

config = configparser.ConfigParser()
config.read(config_file_path)

# Authentication settings
CLIENT_SECRETS_FILE = os.path.abspath(config.get('authentication', 'client_secrets_file'))
OAUTH2_STORAGE_FILE = os.path.abspath(config.get('authentication', 'oauth2_storage_file'))

# Token management settings
FORCE_TOKEN_REFRESH_DAYS = config.getint('token_management', 'force_token_refresh_days')
REFRESH_TIMEOUT = config.getint('token_management', 'refresh_timeout', fallback=30)

# Upload settings
MAX_RETRIES = config.getint('upload_settings', 'MAX_RETRIES')

# Logging settings
LOG_FILE = config.get('logging', 'log_file', fallback='/var/log/youtube_upload.log')
LOG_LEVEL = config.get('logging', 'log_level', fallback='INFO').upper()

# Map string log levels to logging module constants
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Configure logging
logging.basicConfig(
    level=LOG_LEVELS.get(LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# HTTP settings
httplib2.RETRIES = 1
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# OAuth 2.0 and API settings
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
            logger.error(f"Required file {file} does not exist.")
            sys.exit(1)

def refresh_token_with_retry(creds):
    """Attempt to refresh the token with retries."""
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            creds.refresh(Request())  # Removed timeout argument
            logger.info(f"Token refresh successful: new expiry={creds.expiry}")
            # Persist refreshed credentials immediately
            with open(OAUTH2_STORAGE_FILE, 'w') as token:
                json.dump(json.loads(creds.to_json()), token)
                logger.info(f"Refreshed credentials saved to {OAUTH2_STORAGE_FILE}")
            return True
        except HttpError as e:
            logger.error(f"HttpError refreshing token (attempt {retry_count+1}/{MAX_RETRIES}): status={e.resp.status}, content={e.content}")
        except RefreshError as e:
            logger.error(f"RefreshError refreshing token (attempt {retry_count+1}/{MAX_RETRIES}): {e}")
        except urllib.error.URLError as e:
            logger.error(f"Network error refreshing token (attempt {retry_count+1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error refreshing token (attempt {retry_count+1}/{MAX_RETRIES}): {e}")
        retry_count += 1
        sleep_seconds = (2 ** retry_count) + random.random()  # Exponential backoff with jitter
        logger.info(f"Retrying token refresh in {sleep_seconds:.2f} seconds...")
        time.sleep(sleep_seconds)
    logger.error(f"Token refresh failed after {MAX_RETRIES} retries.")
    return False

def get_authenticated_service(args):
    """
    Get an authenticated YouTube service object for headless systems.

    Ensures robust token refresh to avoid manual re-authentication.
    Proactively refreshes tokens before expiry or when invalid.
    Persists credentials after every refresh.
    Compatible with Python 3.9+ using timezone.utc.
    """
    creds = None
    
    if os.path.exists(OAUTH2_STORAGE_FILE):
        try:
            with open(OAUTH2_STORAGE_FILE, 'r') as token:
                creds_data = json.load(token)
            logger.info(f"Loaded credentials data: token={creds_data.get('token', '')[0:10]}..., expiry={creds_data.get('expiry')}")
            creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
            logger.info(f"Existing credentials: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10] if creds.refresh_token else 'None'}...")

            # Current time for comparison with token expiry
            current_time = datetime.now(timezone.utc)  # Timezone-aware UTC
            should_refresh = False
            
            if not creds.refresh_token:
                logger.warning("No refresh token available, forcing new authentication.")
                should_refresh = True
            elif creds.expiry:
                expiry_aware = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry.tzinfo is None else creds.expiry
                time_to_expiry = expiry_aware - current_time
                logger.info(f"Token expiry: {creds.expiry}, time to expiry: {time_to_expiry}")
                should_refresh = (
                    creds.expired or
                    time_to_expiry.total_seconds() < 600 or  # Refresh if less than 10 minutes remaining
                    time_to_expiry.total_seconds() <= FORCE_TOKEN_REFRESH_DAYS * 24 * 60 * 60 or  # Refresh if within refresh window
                    args.force_refresh
                )
            else:
                logger.warning("No expiry set in credentials, forcing refresh.")
                should_refresh = True

            if should_refresh and creds and creds.refresh_token:
                logger.info("Attempting to refresh token.")
                success = refresh_token_with_retry(creds)
                if not success:
                    logger.error("Token refresh failed after retries, forcing new authentication.")
                    os.remove(OAUTH2_STORAGE_FILE)
                    creds = None
                elif not creds.valid:
                    logger.warning("Refreshed token is still invalid, forcing new authentication.")
                    os.remove(OAUTH2_STORAGE_FILE)
                    creds = None
                    
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Invalid or corrupted credentials file ({e}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE)
            creds = None
        except Exception as e:
            logger.error(f"Unexpected error loading credentials ({e}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE)
            creds = None

    if not creds or not creds.valid:
        logger.info("No valid credentials found, initiating manual authentication for headless system.")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account'  # Use select_account to avoid invalidating existing refresh tokens
        )
        
        logger.info(f"Please visit this URL on a device with a browser to authorize the application: {authorization_url}")
        print(f"Please visit this URL to authorize the application:\n{authorization_url}")
        code = input("Enter the authorization code: ").strip()
        logger.info(f"Authorization code entered: {code}")
        
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            logger.info(f"Credentials obtained: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10] if creds.refresh_token else 'None'}...")
            if not creds.expiry:
                logger.warning("No expiry set after initial authentication, setting manually.")
                creds.expiry = datetime.now(timezone.utc) + timedelta(seconds=3600)  # Set to 1 hour
            with open(OAUTH2_STORAGE_FILE, 'w') as token:
                json.dump(json.loads(creds.to_json()), token)
                logger.info(f"Credentials saved to {OAUTH2_STORAGE_FILE}, expiry={creds.expiry}")
        except Exception as e:
            logger.error(f"Failed to fetch token with code: {e}")
            sys.exit(1)

    # Final validation and refresh if necessary
    if creds and (not creds.valid or creds.expired) and creds.refresh_token:
        logger.info("Credentials invalid or expired but refresh token available, attempting final refresh.")
        success = refresh_token_with_retry(creds)
        if not success:
            logger.error("Final refresh attempt failed. Please re-authenticate manually.")
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
    logger.info(f"Video {video_id} added to playlist {playlist_id}")

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Upload a thumbnail for the video if specified."""
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        response = request.execute()
        logger.info(f"Thumbnail uploaded for video {video_id}: {response}")
    except HttpError as e:
        logger.error(f"An error occurred while uploading the thumbnail: {e}")

def resumable_upload(insert_request):
    """Implement resumable upload with exponential backoff strategy."""
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logger.info("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    logger.info(f"Video id '{response['id']}' was successfully uploaded.")
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
            logger.error(error)
            retry += 1
            if retry > MAX_RETRIES:
                sys.exit(f"No longer attempting to retry after {MAX_RETRIES} attempts.")
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logger.info(f"Sleeping {sleep_seconds} seconds and then retrying...")
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
            logger.info("Authentication completed. No video uploaded.")
    except HttpError as e:
        logger.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")