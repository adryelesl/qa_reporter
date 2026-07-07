# QA Reporter Library 🚀

`qa_reporter` is a reusable Python library for generating rich test execution reports from Robot Framework XML results and syncing them with Jira Cloud.

## Features ✨

*   **Email Reports:** Generates HTML email reports with summary charts (Donut) and detailed test logs.
*   **Jira Integration:** Updates Jira issues with execution status, charts, and evidence attachments.
*   **Parameterized:** Works with any folder structure (no hardcoded `frontend`/`backend` assumptions).
*   **Scheduling:** Built-in scheduler to run reports at a specific time daily.

## Prerequisites 🎬

For the library to attach **videos** to your reports, you must enable video recording in your Robot Framework tests (Browser Library).

Example configuration in your `.resource` or `.robot` file:

```robotframework if use Browser Library
New Context    viewport={'width': 1920, 'height': 1080}    recordVideo={'dir': '${OUTPUT_DIR}/browser/video'}
```

*Without this, the library will only attach HTML logs.*

## Installation 📦

### Method 1: Local (Development Mode) - No Git Required 🛠️
To install this library in another project **on your computer** without committing anything:
1. Open your other project's terminal (with venv activated).
2. Run:
   ```bash
   pip install git+https://github.com/adryelesl/qa_reporter.git

   ```
   *(Replace with the actual path to this folder)*

   **Why use `-e`?** This installs in "Editable Mode". Any changes you make here in `src/qa_reporter` will instantly reflect in your other project without reinstalling!

### Method 2: Git (Once pushed) ☁️
```bash
pip install git+ssh://git@github.com/your-org/qa-reporter.git
```

## Configuration ⚙️

Create a `.env` file in your project root with the following variables:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `SMTP_SERVER` | SMTP Server for emails | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP Port | `587` |
| `SMTP_USER` | Email User | `qa@company.com` |
| `SMTP_PASSWORD` | App Password | `xxxx-xxxx-xxxx-xxxx` |
| `SENDER_EMAIL` | From Address | `qa@company.com` |
| `RECIPIENT_EMAIL` | To Address (comma-separated for multiple) | `manager@company.com, qa@company.com` |
| `JIRA_DOMAIN` | Jira Cloud URL | `https://company.atlassian.net` |
| `JIRA_USER_EMAIL` | Jira User Email | `user@company.com` |
| `JIRA_API_TOKEN` | Jira API Token | `abc123xyz` |
| `JIRA_ISSUE_KEY` | Target Issue Key | `QA-1234` |
| `DAILY_EXECUTION_TIME` | (Optional) Format HH:MM (24h) | `14:54` |

*If `DAILY_EXECUTION_TIME` is set, the script will loop and wait for that time each day.*

## Usage 📝

The library provides a built-in terminal command `qa-reporter` that automatically reads your `.env` file and executes the full reporting and Jira sync workflow. No python scripts are needed!

Simply open your terminal (with your virtual environment activated) and run:

```bash
# 1. Run your Robot Framework tests first
robot -d results tests/

# 2. Run the QA Reporter
qa-reporter
```

*That's it!* The `qa-reporter` command will:
1. Generate the HTML report and charts.
2. Send the email (if SMTP config is provided).
3. Sync the results to Jira (if Jira config is provided).

### Scheduled Execution (Daily) 🕒
If you want the report to run automatically every day at a specific time, just add `DAILY_EXECUTION_TIME=14:54` to your `.env` file and run `qa-reporter`. The process will stay open and execute the job every day at the specified time.

## CI/CD Integration & Scheduling ☁️

### 1. GitHub Actions (Recommended for Teams)
To run reports automatically in the cloud, use GitHub Actions.

*   **Template:** Copy the file `workflow_template.yml` from this repo to `.github/workflows/daily_report.yml` in your project.
*   **Scheduling:** The template uses CRON (`cron: '0 11 * * *'`) to run daily at 11:00 UTC.
*   **Secrets:** Add your `.env` variables to GitHub Secrets.
*   **⚠️ IMPORTANT:** Do **NOT** add `DAILY_EXECUTION_TIME` to GitHub Secrets. It will cause the action to timeout (loop forever).

### 2. Local Server (Always On)
If running on a local machine or server that stays on 24/7:
*   Set `DAILY_EXECUTION_TIME=14:54` in your `.env`.
*   Run `qa-reporter` in the terminal.
*   The script will stay open and execute daily at that time.
