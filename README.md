# YouTube Upload Script

Version 1.4.1

## Overview

A Python script for tech enthusiasts looking to automate video uploads to YouTube with the YouTube Data API v3. It handles **OAuth 2.0** authentication, video metadata, and more, all from the command line.

## Key Features

- **Resumable Upload**: The script uses YouTube's resumable upload for handling large files or network issues.
- **Interactive Pause/Resume**: Optional keyboard-driven pause control during uploads with the `--enable-pause` flag.
- **OAuth 2.0**: Configured for offline access and incremental authorization, keeping your app's permissions lean and secure.
- **Improved Retry Logic**: Enhanced exponential backoff with a minimum 30-second delay to respect YouTube API rate limits.
- **Configurable Logging**: Supports customizable log file paths and logging levels for better debugging.
- **Email Notifications**: Optional SMTP email notifications for upload success and failure events.

## How It Works

1. **Authentication**: Uses **OAuth 2.0** for secure access. The script provides a URL for manual entry on headless systems, with automatic token refresh to minimize re-authentication.
    - **Token Management**: Automatically refreshes tokens when they expire, are invalid, or based on a configurable refresh interval. Tokens are stored in `youtube_oauth2_store.json` (file mode `600` after each save).

2. **Upload Process**: 
    - Parses command-line arguments to define video metadata.
    - Initiates a resumable upload to YouTube, with retry logic for reliability.
    - **Enhanced retry timers**: Uses minimum 30-second delays with exponential backoff and jitter to avoid rate limiting.
    - **Optional pause control**: When `--enable-pause` is enabled, press 'p' during upload to pause/resume the upload interactively.
    - Can add videos to playlists, set custom thumbnails, and specify various video settings.

3. **Configuration**: Uses a `config.cfg` file for static settings like paths to credentials, token storage, logging, and retry behavior.

## Usage

**Basic Upload:**
```bash
python3 youtube-upload.py --videofile=path/to/video.mp4 --title="My Video" --description="Cool description"
```

**Upload with pause control:**
```bash
python3 youtube-upload.py --videofile=path/to/video.mp4 --title="My Video" --enable-pause
# Press 'p' during upload to pause, press 'p' again to resume
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
  --publishAt="2026-12-01T08:00:00Z" \
  --publicStatsViewable \
  --madeForKids \
  --ageGroup=age25_34 \
  --gender=female \
  --geo=DE \
  --defaultAudioLanguage=de-DE \
  --enable-pause \
  --force-refresh
```

**Parameters for YouTube Upload**

-   --videofile: Path to the video file you want to upload.
    
-   --title: Video title (default: "Test Title").
    
-   --description: Video description (default: "Test Description").
    
-   --category: Numeric YouTube category ID (default: 22 — People & Blogs).
    
-   --keywords: Comma-separated list of tags (default: "").
    
-   --privacyStatus: Privacy setting (public, private, unlisted; default: public).
    
-   --latitude, --longitude: Set video location (optional). Note: the current YouTube Data API may ignore recording location on upload.
    
-   --language: Default language of the video (default: "en").
    
-   --playlistId: ID of playlist to add video to (optional).
    
-   --thumbnail: Path to thumbnail image file (optional).
    
-   --license: Video license (youtube or creativeCommon; default: youtube).
    
-   --publishAt: Scheduled publish time in ISO 8601 format (optional).
    
-   --publicStatsViewable: Whether video stats should be public (optional).
    
-   --madeForKids: Indicates if the video is made for kids (optional).
    
-   --ageGroup, --gender, --geo: Targeting options for the video (optional). Note: these fields may be ignored by the current YouTube Data API.
   
-   --defaultAudioLanguage: Default audio language (optional).

-   --enable-pause: Enable interactive pause/resume control during upload. Press 'p' to pause/resume (optional).

-   --email: Override recipient email address for notifications. If not provided, uses the address from config.cfg (optional).

**Parameters for authentication or debugging**

-   --no-upload: Authenticate only; don't upload the video.
    
-   --force-refresh: Force token refresh on script run.

## Configuration (config.cfg)

Please rename *config.example.cfg* to *config.cfg* and adjust the parameters accordingly.

```ini
[authentication]
client_secrets_file = /opt/youtube-upload/youtube_client_secrets.json
oauth2_storage_file = /opt/youtube-upload/youtube_oauth2_store.json
force_token_refresh_days = 7

[upload_settings]
MAX_RETRIES = 3

[logging]
log_file = /opt/youtube-upload/youtube_upload.log
log_level = INFO

[mail]
enabled = false
smtp_server = smtp.gmail.com
smtp_port = 587
use_tls = true
smtp_username = your_email@gmail.com
smtp_password = your_password
from_email = your_email@gmail.com
to_email = recipient@example.com
subject_prefix = [YouTube Upload]
```
-   client_secrets_file: Points to your Google API credentials. Use absolute path.
    
-   oauth2_storage_file: Location for storing OAuth tokens. Use absolute path.
    
-   force_token_refresh_days: Days before forcing token refresh (default: 7).
    
-   MAX_RETRIES: Number of retry attempts for upload and token refresh (default: 3). Retries use exponential backoff with a minimum 30-second delay.
    
-   log_file: Path to the log file (default: /opt/youtube-upload/youtube_upload.log if not specified).
    
-   log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

-   enabled: Enable or disable email notifications (true/false; default: false).

-   smtp_server: SMTP server address (e.g., smtp.gmail.com for Gmail).

-   smtp_port: SMTP server port (587 for TLS, 465 for SSL; default: 587).

-   use_tls: Enable TLS encryption (true/false; default: true).

-   smtp_username: SMTP username, usually your email address.

-   smtp_password: SMTP password or app-specific password (for Gmail, use app-specific password).

-   from_email: Sender email address (can be same as smtp_username).

-   to_email: Recipient email address (comma-separated for multiple recipients).

-   subject_prefix: Email subject prefix (default: [YouTube Upload]).

## Setup
### Python

Requires Python 3.10 or higher (pinned Google client libraries dropped 3.9).

### Libraries
```bash
pip install -r requirements.txt
```

### Google API

-   Enable YouTube Data API v3 on Google Cloud Console.
    
-   Create credentials for a Desktop app, download client_secrets.json, and place it at client_secrets_file location.

-   See detailed instructions in [google-console-setup-instructions.md](google-console-setup-instructions.md).
    

### Configuration

-   Rename config.example.cfg to config.cfg and update paths and settings.
    
-   Ensure the user running the script has read/write permissions for client_secrets_file, oauth2_storage_file, and log_file.

-   Restrict secrets on disk: `chmod 600 config.cfg` (SMTP password and credential paths) and `chmod 600` on the OAuth token file (`oauth2_storage_file`). After each token write the script sets the token file mode to `0o600`.

### OAuth out-of-band (OOB) flow

Headless authentication still uses Google's paste-the-code OOB redirect (`urn:ietf:wg:oauth:2.0:oob`): the script prints an authorization URL, you sign in, then paste the code back. Google has **deprecated** this OOB flow; treating the pasted code as a secret is a known risk, and Google may reject OOB for some client types. This release does **not** change that flow.

### Email Notifications (Optional)

To enable email notifications for upload success/failure:

1. Edit the `[mail]` section in `config.cfg`:
   - Set `enabled = true`
   - Configure your SMTP server settings (e.g., Gmail: smtp.gmail.com, port 587)
   - Provide your email credentials (for Gmail, use an [app-specific password](https://support.google.com/accounts/answer/185833))
   - Set recipient email address(es)

2. Example Gmail configuration:
   ```ini
   [mail]
   enabled = true
   smtp_server = smtp.gmail.com
   smtp_port = 587
   use_tls = true
   smtp_username = your_email@gmail.com
   smtp_password = your_app_specific_password
   from_email = your_email@gmail.com
   to_email = recipient@example.com
   subject_prefix = [YouTube Upload]
   ```

3. You can override the recipient email using the `--email` command-line argument:
   ```bash
   python3 youtube-upload.py --videofile=video.mp4 --title="My Video" --email=override@example.com
   ```

## Recent Changes (v1.4.1)

### Docs and dependency hygiene
- Align log file default path in code and README to `/opt/youtube-upload/youtube_upload.log`.
- Document category default `22` (People & Blogs); refresh `publishAt` example year.
- Note that latitude/longitude and age/gender/geo targeting may be ignored by the current YouTube Data API.
- Remove unused `refresh_timeout` / `REFRESH_TIMEOUT` from config example, README, and script load.
- Pin `google-api-python-client>=2.200.0,<3`; replace unused direct `google-auth-httplib2` with direct `httplib2` (script imports `httplib2`).
- Close issue #8: SMTP success/fail notifications already landed; error-only notify flag deferred.

## Recent Changes (v1.4.0)

### Security and hygiene
- Token file (`oauth2_storage_file`) is set to mode `600` after each write.
- Logs no longer include the raw authorization code or access/refresh token prefixes; only non-secret status (path, expiry, whether a refresh token is present).
- Google client libraries are pinned in `requirements.txt` (`google-api-python-client>=2.199.0,<3` and matching pins). Python 3.10+ is required.
- `config.cfg` and the token file should be `chmod 600`.
- OOB paste-the-code authentication is documented as a Google-deprecated known risk; the OOB flow itself is unchanged.

## Recent Changes (v1.3.3)

### Interactive Pause/Resume Feature
- New `--enable-pause` flag enables keyboard-driven pause control during chunked uploads
- Press 'p' during upload to pause, press 'p' again to resume
- Uses non-blocking input via daemon thread to avoid interrupting upload process
- Only shown when flag is explicitly set

### Enhanced Retry Logic
- Updated retry backoff to use **minimum 30-second delays** instead of 2 seconds
- Applies to both token refresh and upload retries
- Formula: `sleep_seconds = max(30, (2 ** retry_count)) + random.random()`
- Prevents rapid retry loops that trigger YouTube API rate limiting

### Improved Error Handling
- All critical error paths verified to exit with status code 1
- Enhanced logging for HttpError, RefreshError, and network errors
- Better handling of authentication failures

## Troubleshooting

- **Rate limiting issues**: The script now uses a minimum 30-second delay between retries to respect YouTube API rate limits.
- **Upload pauses**: If you enabled `--enable-pause`, press 'p' to toggle pause/resume during upload.
- **Token refresh failures**: Check your `oauth2_storage_file` permissions and ensure the `force_token_refresh_days` setting is appropriate.
- **Authentication errors**: Delete the `youtube_oauth2_store.json` file and re-authenticate.

```
