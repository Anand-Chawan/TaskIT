# Generating API Keys for Review Board and JIRA

## 🔐 Overview
This guide **walks** you through the steps to generate API keys or tokens for accessing Review Board and JIRA programmatically. These keys are essential for integrating with automation tools, scripts, or third-party applications.


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


## 🔗 Using the Token securely in scripts.
* Create a *.env* File with below details
JIRA_API_TOKEN=<YOUR API-TOKEN HERE>
REVIEW_BOARD_API_TOKEN=<YOUR API-TOKEN HERE>
TEAMS_API_TOKEN=<YOUR API-TOKEN HERE>

### 📌 Additional Notes
*   Tokens may expire or be revoked; regenerate them if needed.