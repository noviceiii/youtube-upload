# YouTube Video Uploader

This script is designed to upload videos to YouTube using the Google YouTube Data API v3. It handles authentication, video upload with retry logic for better reliability, and allows specifying video details like title, description, category, privacy status, location, and language.
Absolutely no warranty given.

## Create Google Youtube credentials
1. Go to https://console.cloud.google.com/.
2. Create a new project.
3. Choose from menu (or from the console start page) "APIs and services".
4. Click "Library" and search for "Youtube Data API v3", add/allow it.
5. Click on "Credentials" and then "+ Create Credentials". Choose..
    .. "OAuth client ID"
    .. Application type: "Desktop App"
    .. give it a name
6. Download the json of the newly created oAuth client.
7. Save its content as youtube_client_secrets.json - or whatever matches your "client_secrets_file"-path in your config.cfg.


## Prerequisites

- **Python 3.x**
- **Google API Client Library for Python**
  - You can install it via pip:
    ```bash
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```
- **Client Secrets File**
  - Download from Google Developer Console after setting up your YouTube Data API project. Set path in config.cfg to the downloaded file.
- **config.cfg** file with the following content:

    ```ini
    [authentication]
    client_secrets_file = /path/to/your/youtube_client_secrets.json
    oauth2_storage_file = /path/to/your/youtube_oauth2_store.json
    ```

## Usage

### Basic Usage

To upload a video with default settings:

```bash
python youtube-upload.py --videofile "/path/to/your/video.mp4"
```

For manual authentication in environments without local browsers (headless):

```bash
python youtube-upload.py --videofile "/path/to/video.mp4" --nolocalauth
```

## Detailed Usage
Here are the available command-line arguments:
```bash
<span style="color: green">--videofile (required)</span>: Path to the video file you want to upload.
<span style="color: green">--title</span>: Title of the video (default: "Test Title").
<span style="color: green">--description</span>: Description of the video (default: "Test Description").
<span style="color: green">--category</span>: Video category ID (default: "22" which is for "People & Blogs"). Check the YouTube API documentation for valid IDs.
<span style="color: green">--keywords</span>: Keywords for the video, comma separated (default: "").
<span style="color: green">--privacyStatus</span>: Privacy status of the video ("public", "private", "unlisted"; default: "public").
<span style="color: green">--nolocalauth</span>: Use manual authentication instead of local web server (useful if no local browser is available).
<span style="color: green">--latitude</span>: Latitude of where the video was recorded (optional).
<span style="color: green">--longitude</span>: Longitude of where the video was recorded (optional).
<span style="color: green">--language</span>: Language of the video content (default: "en").
```

## Examples
1. Upload a video with custom title and description:

    ```bash
    python youtube-upload.py --videofile "/path/to/video.mp4" --title "My Awesome Video" --description "This is a great video!"

2. Upload with specific privacy status and keywords:
    ```bash
    python youtube-upload.py --videofile "/path/to/video.mp4" --privacyStatus "unlisted" --keywords "python, programming, tutorial"

3. Upload with location information:
    ```bash
    python youtube-upload.py --videofile "/path/to/video.mp4" --latitude 48.8566 --longitude 2.3522 --language "de"

4. Using all parameters:
    ```bash
    python youtube-upload.py  --videofile "/path/to/video.mp4" --title "Epic Journey" --description "A journey through the mountains" --category "17" --keywords "mountains,adventure,hiking" --privacyStatus "public" --nolocalauth --latitude 48.8566 --longitude 2.3522 --language "de"

## Notes
- Ensure that your client_secrets_file and oauth2_storage_file paths in the config.cfg are correct.
- The script will check for the existence of the video file and required configuration files before attempting to upload.
- If authentication fails or credentials are invalid, you will be prompted to re-authenticate.

## Troubleshooting
- If you encounter errors related to file paths, double-check your paths in both the command line and config.cfg.
- For authentication issues, make sure your Google API project has the YouTube Data API enabled and your client secrets are correct.

Happy uploading!

## kudos
See https://developers.google.com/youtube/v3/guides/uploading_a_video for reference.
Thanks to Tokland for the inspiration https://github.com/tokland/youtube-upload.