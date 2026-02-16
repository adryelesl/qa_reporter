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
   pip install -e /Users/adryelesouzaleite/Documents/pj/qa_project
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
| `RECIPIENT_EMAIL` | To Address | `manager@company.com` |
| `JIRA_DOMAIN` | Jira Cloud URL | `https://company.atlassian.net` |
| `JIRA_USER_EMAIL` | Jira User Email | `user@company.com` |
| `JIRA_API_TOKEN` | Jira API Token | `abc123xyz` |
| `JIRA_ISSUE_KEY` | Target Issue Key | `QA-1234` |
| `DAILY_EXECUTION_TIME` | (Optional) Format HH:MM (24h) | `14:54` |

*If `DAILY_EXECUTION_TIME` is set, the script will loop and wait for that time each day.*

## Usage Example 📝

Create a `run_report.py` in your project:

```python
import os
from dotenv import load_dotenv
from qa_reporter.core import run_report
from qa_reporter.jira_client import sync_to_jira
from qa_reporter.scheduler import wait_until_time
import time

load_dotenv()

def main():
    # Load Email Config
    smtp_config = {
        'server': os.getenv('SMTP_SERVER'),
        'port': os.getenv('SMTP_PORT', 587),
        'user': os.getenv('SMTP_USER'),
        'password': os.getenv('SMTP_PASSWORD'),
        'sender': os.getenv('SENDER_EMAIL'),
        'recipient': os.getenv('RECIPIENT_EMAIL')
    }

    # Load Jira Config
    jira_config = {
        'domain': os.getenv('JIRA_DOMAIN'),
        'email': os.getenv('JIRA_USER_EMAIL'),
        'token': os.getenv('JIRA_API_TOKEN'),
        'issue_key': os.getenv('JIRA_ISSUE_KEY')
    }

    # Define job (Updates Email AND Jira)
    def job():
        print("📧 Generating Report & Email...")
        run_report(
            results_dir='results',
            report_dir='report',
            smtp_config=smtp_config
        )
        
        print("🔗 Syncing to Jira...")
        sync_to_jira(
            jira_config=jira_config,
            results_dir='results',
            output_xml_path='output.xml',
            chart_path='report/summary_chart.png',
            video_dir='video'
        )

    # Check for Schedule
    schedule_time = os.getenv('DAILY_EXECUTION_TIME')
    if schedule_time:
        print(f"🕒 Scheduled daily for {schedule_time}")
        while True:
            if not wait_until_time(schedule_time):
                print("❌ Invalid Time Format. Exiting.")
                break
                
            job()
            print("💤 Sleeping for 65s to avoid double trigger...")
            time.sleep(65)
    else:
        print("🚀 Running once (Immediate Mode)...")
        job()

if __name__ == "__main__":
    main()
```

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
*   Run `python run_report.py` manually once.
*   The script will stay open and execute daily at that time.


## Running Tests & Reporting 🏃‍♂️

Usually, you run your tests first, then the report:
```bash
# 1. Run Tests
robot -d results tests/

# 2. Run Report (or keep running for schedule)
python run_report.py
```
