# YouTube Upload Script

Version 1.3

## Overview

A Python script for tech enthusiasts looking to automate video uploads to YouTube with the YouTube Data API v3. It handles **OAuth 2.0** authentication, video metadata, and more, all from the command line. Absolutely no warranty given for anything. Use at your own discretion.

- **Resumable Upload**: The script uses YouTube's resumable upload for handling large files or network issues.
- **OAuth 2.0**: Configured for offline access and incremental authorization, keeping your app's permissions lean and secure.
- **Configurable Logging**: Supports customizable log file paths and logging levels for better debugging.

## How It Works

1. **Authentication**: Uses **OAuth 2.0** for secure access. The script provides a URL for manual entry on headless systems, with automatic token refresh to minimize re-authentication.
    - **Token Management**: Automatically refreshes tokens when they expire, are invalid, or based on a configurable refresh interval. Tokens are stored in `youtube_oauth2_store.json`.

2. **Upload Process**: 
    - Parses command-line arguments to define video metadata.
    - Initiates a resumable upload to YouTube, with retry logic for reliability.
    - Can add videos to playlists, set custom thumbnails, and specify various video settings.

3. **Configuration**: Uses a `config.cfg` file for static settings like paths to credentials, token storage, logging, and retry behavior.

## Usage

**Basic Upload:**
```bash
python3 youtube-upload.py --videofile=path/to/video.mp4 --title="My Video" --description="Cool description"
```

**Advanced usage:**

```bash
python3 youtube-upload.py \
  --videofile=./my_video.mp4 \
  --title="Tech Deep Dive" \
  --description="Exploring the latest in tech" \
  --category=28 \
  --keywords="technology,AI,innovation" \
  --privacyStatus=public \
  --latitude=52.5200 --longitude=13.4050 \
  --language=de \
  --playlistId=PLxYz12345 \
  --thumbnail=./thumbnail.jpg \
  --license=youtube \
  --publishAt="2025-03-01T08:00:00Z" \
  --publicStatsViewable \
  --madeForKids \
  --ageGroup=age25_34 \
  --gender=female \
  --geo=DE \
  --defaultAudioLanguage=de-DE \
  --force-refresh
```
**Parameters for YouTube Upload**

-   --videofile: Path to the video file you want to upload.
    
-   --title: Video title (default: "Test Title").
    
-   --description: Video description (default: "Test Description").
    
-   --category: Numeric YouTube category ID.
    
-   --keywords: Comma-separated list of tags (default: "").
    
-   --privacyStatus: Privacy setting (public, private, unlisted; default: public).
    
-   --latitude, --longitude: Set video location (optional).
    
-   --language: Default language of the video (default: "en").
    
-   --playlistId: ID of playlist to add video to (optional).
    
-   --thumbnail: Path to thumbnail image (optional).
    
-   --license: Video license (youtube or creativeCommon; default: youtube).
    
-   --publishAt: Scheduled publish time in ISO 8601 format (optional).
    
-   --publicStatsViewable: Whether video stats should be public (optional).
    
-   --madeForKids: Indicates if the video is made for kids (optional).
    
-   --ageGroup, --gender, --geo: Targeting options for the video (optional).
   
-   --defaultAudioLanguage: Default audio language (optional).

**Parameters for authentication or debugging**

-   --no-upload: Authenticate only; don't upload the video.
    
-   --force-refresh: Force token refresh on script run.

## Configuration (config.cfg)

Please rename *config.example.cfg* to *config.cfg* and adjust the parameters accordingly.

```ini
[authentication]
client_secrets_file = /opt/youtube-upload/youtube_client_secrets.json
oauth2_storage_file = /opt/youtube-upload/youtube_oauth2_store.json

[token_management]
force_token_refresh_days = 2
refresh_timeout = 30

[upload_settings]
MAX_RETRIES = 3

[logging]
log_file = /opt/youtube-upload/youtube_upload.log
log_level = INFO
```
-   client_secrets_file: Points to your Google API credentials. Use absolute path.
    
-   oauth2_storage_file: Location for storing OAuth tokens. Use absolute path.
    
-   force_token_refresh_days: Days before forcing token refresh (default: 2).
    
-   refresh_timeout: Timeout in seconds for token refresh requests (default: 30, currently not applied due to API limitations).
    
-   MAX_RETRIES: Number of retry attempts for upload and token refresh (default: 3).
    
-   log_file: Path to the log file (default: /var/log/youtube_upload.log if not specified).
    
-   log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

## Setup
### Python

Requires Python 3.9 or higher.

### Libraries
```bash
pip install -r requirements.txt
```

### Google API

-   Enable YouTube Data API v3 on Google Cloud Console.
    
-   Create credentials for a Desktop app, download client_secrets.json, and place it at client_secrets_file location.

-  See detailed instruction in google-console-setup-instructions.md
    

### Configuration

-   Rename config.example.cfg to config.cfg and update paths and settings.
    
-   Ensure the user running the script has read/write permissions for client_secrets_file, oauth2_storage_file, and log_file.
