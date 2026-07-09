import os
from dotenv import load_dotenv
from qa_reporter.core import run_report
from qa_reporter.jira_client import sync_to_jira
from qa_reporter.scheduler import wait_until_time
import time

load_dotenv()

def main():
    smtp_server = os.getenv('SMTP_SERVER')
    
    smtp_config = None
    if smtp_server:
        smtp_config = {
            'server': smtp_server,
            'port': os.getenv('SMTP_PORT', 25),
            'user': os.getenv('SMTP_USER'),
            'password': os.getenv('SMTP_PASSWORD'),
            'sender': os.getenv('SENDER_EMAIL'),
            'recipient': os.getenv('RECIPIENT_EMAIL')
        }
    else:
        print("⚠️ SMTP_SERVER not set. Email sending will be skipped.")

    jira_domain = os.getenv('JIRA_DOMAIN')
    jira_config = None
    if jira_domain:
        jira_config = {
            'domain': jira_domain,
            'email': os.getenv('JIRA_USER_EMAIL'),
            'token': os.getenv('JIRA_API_TOKEN'),
            'issue_key': os.getenv('JIRA_ISSUE_KEY')
        }
    else:
        print("⚠️ JIRA_DOMAIN not set. Jira sync will be skipped.")

    schedule_time = os.getenv('DAILY_EXECUTION_TIME')

    def execute_job():
        print(f"🚀 Starting Scheduled Report Execution at {time.strftime('%H:%M:%S')}...")
        run_report(
            results_dir='results',
            history_file='execution_history.json',
            report_dir='report',
            smtp_config=smtp_config
        )
        
        if jira_config:
            print("🔗 Syncing to Jira...")
            sync_to_jira(
                jira_config=jira_config,
                results_dir='results',
                output_xml_path='output.xml',
                chart_path='report/summary_chart.png',
                video_dir='video',
                requested_tags=os.getenv('TEST_TAGS')
            )

    if schedule_time:
        print(f"🕒 Scheduler Active: Will run daily at {schedule_time}")
        while True:
            # wait_until_time blocks until the time is reached
            wait_until_time(schedule_time)
            
            execute_job()
            
            # Sleep for 65 seconds to ensure we don't trigger the same minute again
            time.sleep(65)
    else:
        # Run once immediately
        execute_job()

if __name__ == "__main__":
    main()
