# Prerequisites
pip install -r requirements.txt

# Generating API Keys for Review Board, JIRA and Teams Calender

## 🔐 Overview
This guide **walks** you through the steps to generate API keys or tokens for accessing Review Board, JIRA and Teams Calender programmatically. These keys are essential for integrating with automation tools, scripts, or third-party applications.


## 🧩 Review Board API Key Generation
### ✅ Prerequisites
*   You must have an active Review Board account.
*   Admin access may be required depending on your organization's configuration.

### 📝 Steps
1. Log in to your Review Board instance.
2. Navigate to the Account Settings:
3. Click on your username in the top-right corner.
4. Select "My Account".
5. Go to the Authentication -> API Tokens section.
6. Click "Generate Token".
7. Provide a name and select the required permissions (e.g., read, write, Full access).
8. Click "Save".
9. Copy the generated token and store it securely.

⚠️ *Note: API tokens are sensitive. Do not share them publicly or commit them to version control.*


## 🧩 JIRA API Token Generation
### ✅ Prerequisites
*   You must have an Jira account.
*   This applies to JIRA Cloud (not Server/Data Center).

### 📝 Steps
1. Log in to your Jira account instance.
2. Navigate to the Account Settings:
3. Click on your username in the top-right corner.
4. Select "Profile".
5. Go to the Personal Access Tokens section.
6. Click "Create token".
7. Enter a label (e.g., "Automation Script").
8. Click "Create".
9. Copy the token and store it securely.

⚠️ *Note: API tokens are sensitive. Do not share them publicly or commit them to version control.*

## 🧩 Teams Calender API Token Generation
### ✅ Prerequisites
*   You must have an active Microsoft Azure account.

### 📝 Steps
1. Register Your App in Azure AD
    Go to Azure Portal
    Navigate to Azure Active Directory > App registrations > New registration
    Fill in: Name: e.g., TeamsCalendarReader
    Supported account types: Choose Single tenant
    Redirect URI: Add one if you're using a web or mobile app (e.g., http://localhost:8080 for testing)

2. Configure API Permissions
    Go to your app registration > API permissions
    Click Add a permission > Microsoft Graph > Delegated permissions
    Add:
    Calendars.Read – to read calendar events
    User.Read – to sign in and read user profile

3. Create a Client Secret
    Go to Certificates & secrets > New client secret
    Add a description and expiration period
    Copy and save the secret value securely (you’ll need it for authentication)


4. Get Tenant ID and Client ID
    From Overview tab of your app registration:
    Copy Application (client) ID
    Copy Directory (tenant) ID

## 🧩 GEMINI AI API Token Generation

### 📝 Steps
1. Go to Google AI Studio.
2. Sign in with your Google account.
3. Click on "Get API Key" in the top-right corner.
4. Copy the key shown — this is your Gemini API key.

## 🔗 Using the Token securely in scripts.
* Create a *.env* File with necessary tokens and load it in code

### 📌 Additional Notes
*   Tokens may expire or be revoked; regenerate them if needed.