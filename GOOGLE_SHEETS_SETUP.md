# Google Sheets API Setup Guide

Follow these steps to enable Google Sheets API access for the analysis system.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "Agentic Workflow")
4. Click "Create"

## Step 2: Enable Google Sheets API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click on it and press "Enable"
4. (Optional) Also enable "Google Drive API" if you need file access

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (or Internal if using Google Workspace)
   - App name: "Agentic Workflow"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: No need to add any (we'll request during auth)
   - Test users: Add your email address
   - Click "Save and Continue"

4. Back to "Create OAuth client ID":
   - Application type: "Desktop app"
   - Name: "Agentic Workflow Desktop"
   - Click "Create"

5. Download the credentials:
   - Click "Download JSON" button
   - Save the file as `credentials.json` in your project root
   - **Important**: `credentials.json` is already in `.gitignore` - never commit it!

## Step 4: First Run Authentication

When you run the analysis script for the first time:

```powershell
py execution\analyze_sheet_structure.py "YOUR_SHEET_URL"
```

1. A browser window will open
2. Sign in with your Google account
3. Click "Continue" when warned about unverified app (if in test mode)
4. Grant access to "See all your Google Sheets spreadsheets"
5. The browser will show "The authentication flow has completed"
6. Close the browser and return to the terminal

A `token.json` file will be created and saved for future runs (no browser needed next time).

## Step 5: Test the Setup

Test with a public or your own Google Sheet:

```powershell
py execution\analyze_sheet_structure.py "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

## Troubleshooting

### Error: "credentials.json not found"
- Make sure you downloaded the OAuth credentials from Google Cloud Console
- Save it as `credentials.json` in the project root (same directory as AGENTS.md)

### Error: "Invalid authentication credentials"
- Delete `token.json` and try again
- Make sure you're using OAuth 2.0 credentials, not API key or Service Account

### Error: "Access denied" / "Permission denied"
- Make sure the Google Sheet is accessible by your Google account
- Check sharing settings of the sheet
- For organization sheets, you may need internal app approval

### Browser doesn't open during auth
- Look for a URL in the terminal and copy it to your browser manually
- Check if your firewall is blocking localhost connections

## Security Notes

- `credentials.json` contains your OAuth client ID (not secret, but keep private)
- `token.json` contains your access token (sensitive, never commit)
- Both files are in `.gitignore` by default
- Tokens expire and auto-refresh
- You can revoke access anytime from [Google Account](https://myaccount.google.com/permissions)

## Publishing Your App (Optional)

If you want to share this tool with others:
1. Complete the OAuth consent screen fully
2. Submit for Google verification
3. Once verified, users won't see the "unverified app" warning

For personal/internal use, test mode is sufficient.
