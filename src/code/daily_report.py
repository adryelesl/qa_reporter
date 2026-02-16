import os
from dotenv import load_dotenv
from qa_reporter.core import run_report
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

    schedule_time = os.getenv('DAILY_EXECUTION_TIME')

    def execute_job():
        print(f"🚀 Starting Scheduled Report Execution at {time.strftime('%H:%M:%S')}...")
        run_report(
            results_dir='results',
            history_file='execution_history.json',
            report_dir='report',
            smtp_config=smtp_config
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
