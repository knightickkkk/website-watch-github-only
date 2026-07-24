# Website Watch: GitHub-Only Version

This is the no-paid-hosting version.

It uses:

- GitHub Pages for the public form.
- GitHub Issues as the request database.
- GitHub Actions as the daily scheduler.
- Gmail SMTP to send screenshot emails.

No Render, no backend server, no paid hosting.

## Important Limits

This is free and simple, but there are tradeoffs:

- Users need a GitHub account to submit the pre-filled issue.
- If the repo is public, submitted emails and website URLs are visible in issues.
- If the repo is private, only collaborators can submit issues.
- You still need a Gmail App Password in GitHub Secrets to send emails with screenshot attachments.

If you want a normal public form with private submissions and no GitHub account requirement, you need a backend/form provider somewhere.

## How Users Submit

1. User opens your GitHub Pages website.
2. User enters:
   - email
   - website URL
   - optional CSS selector
3. The page opens a pre-filled GitHub Issue.
4. User clicks **Submit new issue**.
5. GitHub Actions reads open issues labeled `watch-request`.
6. Every day at 12:00 AM IST, the workflow checks all submitted websites.
7. If a page changes after its first baseline run, the user gets an email with a screenshot attached.

## Setup

Upload this whole folder to a GitHub repo.

Then edit:

```text
docs/config.js
```

Set your repo URL:

```js
window.WATCH_REPO_URL = "https://github.com/YOUR_USERNAME/YOUR_REPO";
```

## Enable GitHub Pages

In GitHub:

1. Go to `Settings` -> `Pages`.
2. Source: `Deploy from a branch`.
3. Branch: `main`.
4. Folder: `/docs`.
5. Save.

Your form will be available at a URL like:

```text
https://YOUR_USERNAME.github.io/YOUR_REPO/
```

## Add GitHub Secrets

Go to:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Add:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-bot-gmail@gmail.com
SMTP_PASSWORD=your-16-character-gmail-app-password
MAIL_FROM=your-bot-gmail@gmail.com
```

Use the Gmail App Password, not your normal Gmail password.

## Run It

Go to:

```text
Actions -> Daily Website Watch -> Run workflow
```

The first run creates baselines and usually sends no alert. Future runs send emails when pages change.

The workflow also runs automatically every day at:

```text
12:00 AM IST
```

## Issue Format

The form creates issues like this:

```text
Email: user@example.com
Website: https://example.com
Selector:
Compare mode: text
```

Do not rename those field labels unless you also update the parser.
