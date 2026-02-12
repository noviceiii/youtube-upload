#!/usr/bin/env python3

# This script uploads a video to YouTube using the YouTube Data API v3.
# It uses OAuth 2.0 for authentication, adapted for headless systems.
# Supports resumable uploads, video metadata, thumbnail uploads, and playlist addition.
# Automatically refreshes tokens to prevent manual re-authentication.
# Exits with non-zero status code on critical upload errors (e.g., 400 uploadLimitExceeded).
# Validates configuration file paths and exits with meaningful errors if invalid.
# @version 1.3.3, 2025-09-26

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

from googleapiclient.discovery import build  # Build API client
from googleapiclient.errors import HttpError  # Handle API errors
from googleapiclient.http import MediaFileUpload  # Handle file uploads
from google_auth_oauthlib.flow import InstalledAppFlow  # OAuth flow for authentication
from google.auth.exceptions import RefreshError  # Handle token refresh errors
from google.auth.transport.requests import Request  # HTTP request for token refresh
from google.oauth2.credentials import Credentials  # Manage OAuth credentials
import urllib.error  # Handle URL-related errors

# Load configuration from config.cfg
config_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.cfg')  # Path to config file
try:
    config = configparser.ConfigParser()  # Initialize config parser
    config.read(config_file_path)  # Read config file
    if not config.sections():  # Check if config file is empty or invalid
        raise configparser.Error("Config file is empty or malformed")
except (configparser.Error, OSError, PermissionError) as e:
    print(f"Error: Failed to read configuration file '{config_file_path}': {e}")
    sys.exit(1)  # Exit with non-zero status code

# Authentication settings
try:
    CLIENT_SECRETS_FILE = os.path.abspath(config.get('authentication', 'client_secrets_file'))  # Path to client_secrets.json
    OAUTH2_STORAGE_FILE = os.path.abspath(config.get('authentication', 'oauth2_storage_file', fallback='/opt/Python Scripts/youtube-upload/youtube_oauth2_store.json'))  # Path to token storage
    FORCE_TOKEN_REFRESH_DAYS = config.getint('authentication', 'force_token_refresh_days', fallback=7)  # Days before forcing token refresh
    REFRESH_TIMEOUT = config.getint('authentication', 'refresh_timeout', fallback=30)  # Timeout for token refresh attempts
except configparser.NoSectionError as e:
    print(f"Error: Missing [authentication] section in config file: {e}")
    sys.exit(1)
except configparser.NoOptionError as e:
    print(f"Error: Missing required option in [authentication] section: {e}")
    sys.exit(1)

# Upload settings
try:
    MAX_RETRIES = config.getint('upload_settings', 'MAX_RETRIES', fallback=3)  # Max retries for uploads and token refresh
except configparser.NoSectionError as e:
    print(f"Error: Missing [upload_settings] section in config file: {e}")
    sys.exit(1)

# Logging settings
try:
    LOG_FILE = config.get('logging', 'log_file', fallback='/opt/Python Scripts/youtube-upload/youtube_upload.log')  # Path to log file
    LOG_LEVEL = config.get('logging', 'log_level', fallback='INFO').upper()  # Log level (e.g., INFO, DEBUG)
except configparser.NoSectionError as e:
    print(f"Error: Missing [logging] section in config file: {e}")
    sys.exit(1)

# Map string log levels to logging module constants
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Configure logging
try:
    logging.basicConfig(
        level=LOG_LEVELS.get(LOG_LEVEL, logging.INFO),  # Set log level
        format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
        handlers=[
            logging.FileHandler(LOG_FILE),  # Log to file
            logging.StreamHandler()  # Log to console
        ]
    )
except (OSError, PermissionError) as e:
    print(f"Error: Cannot configure logging to '{LOG_FILE}': {e}")
    sys.exit(1)  # Exit with non-zero status code
logger = logging.getLogger(__name__)  # Initialize logger

# HTTP settings
httplib2.RETRIES = 1  # Set HTTP retries to 1
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]  # HTTP status codes to retry
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine
)  # Exceptions to retry

# OAuth 2.0 and API settings
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]  # OAuth scopes
YOUTUBE_API_SERVICE_NAME = "youtube"  # YouTube API service name
YOUTUBE_API_VERSION = "v3"  # YouTube API version

# Error message for missing client_secrets.json
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

def check_files():
    """Check if required files and directories exist and are accessible."""
    # Validate client_secrets_file
    if not os.path.exists(CLIENT_SECRETS_FILE):
        logger.error(f"Client secrets file '{CLIENT_SECRETS_FILE}' does not exist.")
        print(MISSING_CLIENT_SECRETS_MESSAGE)
        sys.exit(1)  # Exit with non-zero status code
    if not os.path.isfile(CLIENT_SECRETS_FILE):
        logger.error(f"Path '{CLIENT_SECRETS_FILE}' is not a valid file.")
        sys.exit(1)  # Exit with non-zero status code

    # Validate oauth2_storage_file directory
    oauth2_dir = os.path.dirname(OAUTH2_STORAGE_FILE)
    if not os.path.exists(oauth2_dir):
        logger.error(f"Directory for OAuth storage file '{oauth2_dir}' does not exist.")
        sys.exit(1)  # Exit with non-zero status code
    if not os.access(oauth2_dir, os.W_OK):
        logger.error(f"Directory for OAuth storage file '{oauth2_dir}' is not writable.")
        sys.exit(1)  # Exit with non-zero status code

    # Validate log_file directory
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        logger.error(f"Directory for log file '{log_dir}' does not exist.")
        sys.exit(1)  # Exit with non-zero status code
    if not os.access(log_dir, os.W_OK):
        logger.error(f"Directory for log file '{log_dir}' is not writable.")
        sys.exit(1)  # Exit with non-zero status code

def load_tokens():
    """Load OAuth tokens from file or return None if not found."""
    if os.path.exists(OAUTH2_STORAGE_FILE):  # Check if token file exists
        try:
            with open(OAUTH2_STORAGE_FILE, "r") as f:
                logger.info(f"Loading tokens from {OAUTH2_STORAGE_FILE}")
                return json.load(f)  # Read token JSON
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load OAuth tokens from '{OAUTH2_STORAGE_FILE}': {e}")
            os.remove(OAUTH2_STORAGE_FILE) if os.path.exists(OAUTH2_STORAGE_FILE) else None
            return None
    logger.warning(f"No token file found at {OAUTH2_STORAGE_FILE}, new authentication required.")
    return None

def save_tokens(credentials):
    """Save OAuth tokens to file."""
    tokens = {  # Construct token dictionary
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "token_uri": credentials.token_uri,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None
    }
    try:
        with open(OAUTH2_STORAGE_FILE, "w") as f:  # Write tokens to file
            json.dump(tokens, f)
            logger.info(f"Credentials saved to {OAUTH2_STORAGE_FILE}, expiry={credentials.expiry}")
    except OSError as e:
        logger.error(f"Failed to save OAuth tokens to '{OAUTH2_STORAGE_FILE}': {e}")
        sys.exit(1)  # Exit with non-zero status code

def refresh_token_with_retry(creds):
    """Attempt to refresh the token with retries."""
    retry_count = 0
    while retry_count < MAX_RETRIES:  # Retry up to MAX_RETRIES
        try:
            creds.refresh(Request())  # Attempt token refresh
            logger.info(f"Token refresh successful: new expiry={creds.expiry}")
            save_tokens(creds)  # Save refreshed tokens
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
    """
    creds = None
    tokens = load_tokens()  # Load existing tokens
    if tokens:
        try:
            creds = Credentials(  # Initialize credentials from tokens
                token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                client_id=tokens["client_id"],
                client_secret=tokens["client_secret"],
                token_uri=tokens["token_uri"],
                scopes=tokens["scopes"]
            )
            logger.info(f"Loaded credentials: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10] if creds.refresh_token else 'None'}...")

            # Check token expiry and refresh proactively
            current_time = datetime.now(timezone.utc)  # Get current UTC time
            should_refresh = False
            if not creds.refresh_token:  # No refresh token
                logger.warning("No refresh token available, forcing new authentication.")
                should_refresh = True
            elif creds.expiry:
                expiry_aware = creds.expiry
                if creds.expiry.tzinfo is None:  # Ensure timezone-aware expiry
                    expiry_aware = creds.expiry.replace(tzinfo=timezone.utc)
                time_to_expiry = expiry_aware - current_time
                logger.info(f"Token expiry: {creds.expiry}, time to expiry: {time_to_expiry}")
                should_refresh = (
                    creds.expired or  # Token is expired
                    time_to_expiry.total_seconds() < 600 or  # Less than 10 minutes remaining
                    time_to_expiry.total_seconds() <= FORCE_TOKEN_REFRESH_DAYS * 24 * 60 * 60 or  # Within refresh window
                    args.force_refresh  # Forced refresh via argument
                )
            else:
                logger.warning("No expiry set in credentials, forcing refresh.")
                should_refresh = True

            if should_refresh and creds.refresh_token:
                logger.info("Attempting to refresh token.")
                success = refresh_token_with_retry(creds)  # Try refreshing token
                if not success or not creds.valid:
                    logger.error("Token refresh failed or token still invalid, forcing new authentication.")
                    os.remove(OAUTH2_STORAGE_FILE) if os.path.exists(OAUTH2_STORAGE_FILE) else None  # Remove invalid token file
                    creds = None
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Invalid or corrupted credentials file ({e}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE) if os.path.exists(OAUTH2_STORAGE_FILE) else None  # Remove corrupted file
            creds = None
        except Exception as e:
            logger.error(f"Unexpected error loading credentials ({e}), initiating new authentication.")
            os.remove(OAUTH2_STORAGE_FILE) if os.path.exists(OAUTH2_STORAGE_FILE) else None
            creds = None

    if not creds or not creds.valid:  # No valid credentials, start new authentication
        logger.info("No valid credentials found, initiating manual authentication for headless system.")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"  # Headless OAuth flow
        )
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # Enable refresh token
            include_granted_scopes='true',
            prompt='select_account'  # Avoid invalidating existing tokens
        )
        logger.info(f"Please visit this URL to authorize the application: {authorization_url}")
        print(f"Please visit this URL to authorize the application:\n{authorization_url}")
        code = input("Enter the authorization code: ").strip()  # Get auth code from user
        logger.info(f"Authorization code entered: {code}")

        try:
            flow.fetch_token(code=code)  # Exchange code for tokens
            creds = flow.credentials
            logger.info(f"Credentials obtained: token={creds.token[:10]}..., expiry={creds.expiry}, refresh_token={creds.refresh_token[:10] if creds.refresh_token else 'None'}...")
            if not creds.expiry:  # Set default expiry if none provided
                logger.warning("No expiry set after initial authentication, setting manually.")
                creds.expiry = datetime.now(timezone.utc) + timedelta(seconds=3600)
            save_tokens(creds)  # Save new credentials
        except Exception as e:
            logger.error(f"Failed to fetch token with code: {e}")
            sys.exit(1)

    # Final validation and refresh
    if creds and (not creds.valid or creds.expired) and creds.refresh_token:
        logger.info("Credentials invalid or expired but refresh token available, attempting final refresh.")
        success = refresh_token_with_retry(creds)
        if not success:
            logger.error("Final refresh attempt failed. Please re-authenticate manually.")
            os.remove(OAUTH2_STORAGE_FILE) if os.path.exists(OAUTH2_STORAGE_FILE) else None
            sys.exit(1)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)  # Return authenticated API client

def initialize_upload(youtube, options):
    """Initialize and execute the upload process for a video to YouTube."""
    tags = None
    if options.keywords:  # Split keywords if provided
        tags = options.keywords.split(",")

    body = dict(  # Construct video metadata
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

    if options.ageGroup or options.gender or options.geo:  # Add targeting if specified
        body['status']['targeting'] = {}
        if options.ageGroup:
            body['status']['targeting']['ageGroup'] = options.ageGroup
        if options.gender:
            body['status']['targeting']['genders'] = [options.gender]
        if options.geo:
            body['status']['targeting']['countries'] = options.geo.split(',')

    try:
        insert_request = youtube.videos().insert(  # Create upload request
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(options.videofile, chunksize=-1, resumable=True)  # Enable resumable upload
        )

        response = resumable_upload(insert_request)  # Perform upload
        if response is None:  # Check if upload failed
            logger.error("Upload failed after retries.")
            sys.exit(1)  # Exit with non-zero status code

        if options.thumbnail:  # Upload thumbnail if provided
            upload_thumbnail(youtube, response['id'], options.thumbnail)

        if options.playlistId:  # Add to playlist if specified
            add_video_to_playlist(youtube, response['id'], options.playlistId)

    except HttpError as e:  # Handle critical HTTP errors (e.g., 400 uploadLimitExceeded)
        logger.error(f"Critical HTTP error during upload: status={e.resp.status}, content={e.content}")
        sys.exit(1)  # Exit with non-zero status code
    except Exception as e:  # Handle other unexpected errors
        logger.error(f"Unexpected error during upload: {e}")
        sys.exit(1)  # Exit with non-zero status code

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
    response = add_video_request.execute()  # Execute playlist addition
    logger.info(f"Video {video_id} added to playlist {playlist_id}")

def upload_thumbnail(youtube, video_id, thumbnail_path):
    """Upload a thumbnail for the video if specified."""
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)  # Upload thumbnail file
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
    while response is None and retry <= MAX_RETRIES:  # Retry up to MAX_RETRIES
        try:
            logger.info("Uploading file...")
            status, response = insert_request.next_chunk()  # Upload next chunk
            if response is not None:
                if 'id' in response:  # Check if upload succeeded
                    logger.info(f"Video id '{response['id']}' was successfully uploaded.")
                    return response
                else:
                    raise Exception(f"The upload failed with an unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:  # Retry on specific HTTP errors
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                logger.error(f"Non-retriable HTTP error {e.resp.status} occurred: {e.content}")
                raise  # Raise non-retriable errors (e.g., 400)
        except RETRIABLE_EXCEPTIONS as e:  # Retry on specific exceptions
            error = f"A retriable error occurred: {e}"

        if error is not None:
            logger.error(error)
            retry += 1
            if retry > MAX_RETRIES:  # Return None if max retries exceeded
                logger.error(f"Upload failed after {MAX_RETRIES} retries.")
                return None
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep  # Exponential backoff
            logger.info(f"Sleeping {sleep_seconds} seconds and then retrying...")
            time.sleep(sleep_seconds)

    return None

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()  # Initialize argument parser
    parser.add_argument("--videofile", help="Video file to upload")
    parser.add_argument("--title", help="Video title", default="Test Title")
    parser.add_argument("--description", help="Video description", default="Test Description")
    parser.add_argument("--category", default="22", help="Numeric video category.")
    parser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    parser.add_argument("--privacyStatus", choices=["public", "private", "unlisted"], default="public", help="Video privacy status.")
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

    args = parser.parse_args()  # Parse command-line arguments

    if not args.no_upload and not args.videofile:  # Check for required video file
        logger.error("Please specify a valid file using the --videofile= parameter if not using --no-upload.")
        sys.exit(1)  # Exit with non-zero status code

    check_files()  # Verify required files and directories

    youtube = get_authenticated_service(args)  # Get authenticated API client
    try:
        if not args.no_upload:  # Perform upload if not in no-upload mode
            initialize_upload(youtube, args)
        else:
            logger.info("Authentication completed. No video uploaded.")
    except HttpError as e:  # Handle critical HTTP errors during upload
        logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
        sys.exit(1)  # Exit with non-zero status code
    except Exception as e:  # Handle other unexpected errors
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)  # Exit with non-zero status code
