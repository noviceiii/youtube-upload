# Google API Setup Instructions for YouTube Upload

## Create a New Project in Google Cloud Console

1. Go to the Google Cloud Console.
2. Click the project dropdown at the top of the page (near the Google Cloud logo).
3. Click **New Project** in the project selection dialog.
4. Enter a Project name (e.g., *YouTubeUploadScript*).
5. Optionally, select an Organization or leave it as "No organization."
6. Click **Create**.
7. Once created, select the new project from the project dropdown to ensure you're working in its context.

## Enable the YouTube Data API v3

1. In the Google Cloud Console, navigate to **APIs & Services** > **Library** in the left-hand menu.
2. Search for "YouTube Data API v3".
3. Click on **YouTube Data API v3** and then click **Enable**.
    - If prompted, confirm the project selection.
4. Wait for the API to be enabled (this may take a few seconds).

## Configure the OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen** in the left-hand menu.
2. Select the User Type:
    - Choose **External** if the script will be used by users outside your organization (most common for personal projects).
    - Choose **Internal** if the script is only for users within a Google Workspace organization.
3. Click **Create**.
4. Fill in the App information:
    - **App name**: Enter a name (e.g., YouTube Uploader).
    - **User support email**: Select or enter your email address.
    - **Developer contact information**: Enter your email address.
5. Under App domain, you can leave the fields blank unless you have specific URLs.
6. Click **Save and Continue**.
7. On the Scopes page:
    - Click **Add or Remove Scopes**.
    - Search for and select the following scopes:
      - `https://www.googleapis.com/auth/youtube.upload`
      - `https://www.googleapis.com/auth/youtube`
    - Click **Update**, then **Save and Continue**.
8. On the Test users page (if you selected External):
    - Add your Google account email as a test user to allow testing without publishing.
    - Click **Save and Continue**.
9. Review the Summary page and click **Back to Dashboard**.

## Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials** in the left-hand menu.
2. Click **Create Credentials** at the top and select **OAuth 2.0 Client IDs**.
3. Configure the OAuth client:
    - **Application type**: Select Desktop app.
    - **Name**: Enter a name (e.g., YouTube Uploader Desktop Client).
    - Leave other fields as default.
4. Click **Create**.
5. Download the credentials:
    - In the OAuth 2.0 Client IDs section, find your new client ID.
    - Click the Download button (download icon) to download the `client_secrets.json` file.
6. Save the `client_secrets.json` file to the directory specified in your script's `config.cfg` file (e.g., the path set for `client_secrets_file`).