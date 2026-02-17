import os
import json
import shutil
import smtplib
import glob
import subprocess
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from datetime import datetime
import matplotlib.pyplot as plt
import os
import json
import shutil
import smtplib
import glob
import subprocess
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from datetime import datetime
import matplotlib.pyplot as plt
from robot.api import ExecutionResult
from .metrics import TestMetrics

def load_history(history_file):
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return {}

def save_history(history, history_file):
    # Ensure dir exists
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

def clean_log_video(log_path, new_screenshot_name=None):
    if not os.path.exists(log_path):
        return

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern_video = r'(<video.+?\\x3c/video>)|(\\x3cvideo.+?\\x3c/video>)'
        replacement_video = r'<b>Video evidence available in project folder</b>'
        content = re.sub(pattern_video, replacement_video, content, flags=re.DOTALL)
        
        if new_screenshot_name:
            content = re.sub(r'browser/screenshot/[^"]+\.png', new_screenshot_name, content)
        else:
            content = content.replace('browser/screenshot/', '')
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(content)
                
    except Exception as e:
        print(f"Error cleaning log {log_path}: {e}")

def manage_evidence(tests, history, results_dir):
    # Base video dir within results
    base_video_dir = os.path.join(results_dir, 'video')
    
    # We infer categories from tests to create subdirectories
    categories = set(t['category'] for t in tests)
    for category in categories:
        path = os.path.join(base_video_dir, category)
        os.makedirs(path, exist_ok=True)

    updated_history = history.copy()
    current_date = datetime.now().strftime('%d_%m_%y')

    print(f"Processing evidence for {len(tests)} tests...")

    for test in tests:
        test_id = test['id'] or test['name'] # Fallback
        category = test['category']
            
        target_name = f"{test_id}_{current_date}"
        target_dir = os.path.join(base_video_dir, category)
        
        status = test['status']
        is_first_run = test_id not in history
        
        should_keep = False
        if status == 'SKIP':
            should_keep = False
        elif is_first_run:
            should_keep = True
        elif status == 'FAIL':
            should_keep = True
        else:
            should_keep = False

        video_source_path = None
        screenshot_source_path = None
        
        # Look for source files relative to results_dir
        for msg in test['messages']:
            if 'video' in msg and '.webm' in msg:
                match = re.search(r'src="([^"]+\.webm)"', msg)
                if match:
                    rel_path = match.group(1)
                    full_path = os.path.join(results_dir, rel_path)
                    if os.path.exists(full_path):
                        video_source_path = full_path

            if 'screenshot' in msg and '.png' in msg:
                 match = re.search(r'src="([^"]+\.png)"', msg)
                 if match:
                    rel_path = match.group(1)
                    full_path = os.path.join(results_dir, rel_path)
                    if os.path.exists(full_path):
                        screenshot_source_path = full_path

        final_video_path = os.path.join(target_dir, f"{target_name}.webm")
        final_log_path = os.path.join(target_dir, f"{target_name}.html")
        
        final_screenshot_name = None
        final_screenshot_path = None
        if screenshot_source_path:
            final_screenshot_name = f"{target_name}_FAIL.png"
            final_screenshot_path = os.path.join(target_dir, final_screenshot_name)

        if should_keep:
            if video_source_path:
                shutil.copy(video_source_path, final_video_path)
            
            if screenshot_source_path and final_screenshot_path:
                shutil.copy(screenshot_source_path, final_screenshot_path)

            # Generate individual log using rebot
            # We assume output.xml is at results_dir/output.xml, user must ensure this structure or pass path
            output_xml_path = os.path.join(results_dir, 'output.xml')
             
            subprocess.run([
                'rebot',
                '--log', final_log_path,
                '--report', 'NONE',
                '--output', 'NONE',
                '--test', test['name'],
                output_xml_path
            ], check=False, stdout=subprocess.DEVNULL)
            
            clean_log_video(final_log_path, final_screenshot_name)

        updated_history[test_id] = {
            'status': status,
            'last_run': datetime.now().isoformat(),
            'kept_evidence': should_keep,
            'evidence_paths': {
                'video': final_video_path if should_keep and video_source_path else None,
                'log': final_log_path if should_keep else None,
                'screenshot': final_screenshot_path if should_keep and screenshot_source_path else None
            }
        }

    # Cleanup Source Video/Traces
    video_source_root = os.path.join(results_dir, 'browser', 'video')
    if os.path.exists(video_source_root):
        try:
            shutil.rmtree(video_source_root)
        except: pass
            
    traces_dir = os.path.join(results_dir, 'browser', 'traces')
    if os.path.exists(traces_dir):
        try:
            shutil.rmtree(traces_dir)
        except: pass

    return updated_history

def generate_chart(metrics, report_dir):
    labels = ['Passed', 'Failed', 'Skipped']
    sizes = [metrics.passed, metrics.failed, metrics.skipped]
    colors = ['#00C896', '#D32F2F', '#B0BEC5'] 
    
    total = metrics.total if metrics.total > 0 else 1
    pass_rate = (metrics.passed / total) * 100
    
    clean_labels = []
    clean_sizes = []
    clean_colors = []
    for i in range(len(sizes)):
        if sizes[i] > 0:
            clean_labels.append(labels[i])
            clean_sizes.append(sizes[i])
            clean_colors.append(colors[i])

    # Horizontal Layout (12x6) - Library Default
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={'width_ratios': [6, 4]})
    fig.patch.set_facecolor('white')
    
    if not clean_sizes:
        clean_sizes = [1]
        clean_colors = ['#E0E0E0']
        pass_rate = 0
    
    wedges, texts, autotexts = ax1.pie(clean_sizes, 
                                      colors=clean_colors, 
                                      autopct='%1.0f%%', 
                                      startangle=90, 
                                      pctdistance=0.85,
                                      wedgeprops=dict(width=0.4, edgecolor='white'),
                                      textprops={'fontsize': 16, 'weight': 'bold', 'color': 'white'}
                                      )
    
    ax1.text(0, 0, f"{int(pass_rate)}%", ha='center', va='center', fontsize=42, fontweight='bold', color='#333')
    ax1.text(0, -0.25, "PASSED", ha='center', va='center', fontsize=16, color='#666')
    ax1.axis('equal')

    ax2.axis('off')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    
    def draw_legend_row(y, label, count, color, total_count):
        pct = (count / total_count * 100) if total_count > 0 else 0
        x_dot = 0.1
        x_label = 0.25
        x_val = 0.6
        x_pct = 0.8
        
        ax2.scatter([x_dot], [y], s=800, c=color, marker='o') 
        ax2.text(x_label, y, f"{label}", fontsize=18, va='center', fontweight='bold', color='#444')
        ax2.text(x_val, y, f"{count}", fontsize=18, va='center', fontweight='bold', color='#333')
        ax2.text(x_pct, y, f"({int(pct)}%)", fontsize=16, va='center', color='#777')

    draw_legend_row(0.7, "Passed", metrics.passed, '#00C896', total)
    draw_legend_row(0.5, "Failed", metrics.failed, '#D32F2F', total)
    draw_legend_row(0.3, "Skipped", metrics.skipped, '#B0BEC5', total)
    
    ax2.text(0.1, 0.1, f"Total Tests: {metrics.total}", fontsize=16, style='italic', color='#888')

    plt.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1, wspace=0.1)

    chart_path = os.path.join(report_dir, 'summary_chart.png')
    # Ensure report dir
    os.makedirs(report_dir, exist_ok=True)
    
    plt.savefig(chart_path, dpi=100)
    plt.close()
    return chart_path

def format_duration(ms):
    seconds = int(ms / 1000)
    milliseconds = int((ms % 1000) / 10)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{milliseconds:02d}"

def format_date_display(rf_timestamp):
    try:
        dt = datetime.strptime(rf_timestamp.split('.')[0], '%Y%m%d %H:%M:%S')
        return dt.strftime('%d-%m-%Y %H:%M')
    except:
        return rf_timestamp

def generate_html_report_body(metrics, chart_path, history, report_dir):
    total_duration_ms = sum(t['elapsed_time'] for t in metrics.tests)
    total_duration_str = format_duration(total_duration_ms)
    last_exec_raw = max((t['end_time'] for t in metrics.tests), default="")
    last_exec_str = format_date_display(last_exec_raw) if last_exec_raw else "N/A"

    # Group tests dynamically by category
    tests_by_category = {}
    for t in metrics.tests:
        cat = t['category']
        if cat not in tests_by_category:
            tests_by_category[cat] = []
        tests_by_category[cat].append(t)
    
    # Sort categories and tests
    sorted_categories = sorted(tests_by_category.keys())
    for cat in sorted_categories:
        tests_by_category[cat].sort(key=lambda x: x['id'])

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
            .pass { color: green; font-weight: bold; }
            .fail { color: red; font-weight: bold; }
            .skip { color: #888888; font-weight: bold; }
            .container-table { border: none; width: 100%; }
            .container-td {{ border: none; vertical-align: top; padding: 10px; }}
            .info-box {{
                display: inline-block;
                border: 1px solid #dddddd;
                background-color: #f9f9f9;
                border-radius: 5px;
                padding: 10px;
                margin-right: 15px;
                text-align: center;
                color: #333;
                font-family: Arial, sans-serif;
            }}
            .info-label {{ display: block; font-size: 0.9em; margin-bottom: 5px; color: #666; }}
            .info-value {{ display: block; font-size: 1.4em; }}
            summary {{ cursor: pointer; font-weight: bold; font-size: 1.1em; margin-bottom: 10px; padding: 5px; background-color: #eee; }}
        </style>
    </head>
    <body>
        <h2>Daily Test Execution Report</h2>
        
        <table class="container-table">
            <tr style="border: none;">
                <td class="container-td" style="width: 40%;">
                    <img src="cid:summary_chart" alt="Summary Chart" width="100%">
                </td>
                <td class="container-td" style="width: 60%;">
                    <h3>Summary</h3>
                    <table>
                        <tr>
                            <th>Total</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Skipped</th>
                        </tr>
                        <tr>
                            <td>{metrics.total}</td>
                            <td class="pass">{metrics.passed}</td>
                            <td class="fail">{metrics.failed}</td>
                            <td>{metrics.skipped}</td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 20px;">
                        <div class="info-box">
                            <span class="info-label">Tempo Total de Execução</span>
                            <span class="info-value">{total_duration_str}</span>
                        </div>
                        <div class="info-box">
                            <span class="info-label">Data da Ultima Execução</span>
                            <span class="info-value">{last_exec_str}</span>
                        </div>
                    </div>
                </td>
            </tr>
        </table>
        
        <h3>Detailed Execution</h3>
    """

    def render_table(tests, title):
        if not tests: return ""
        
        table_html = f"""
        <details open>
            <summary>{title} ({len(tests)})</summary>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Details</th>
                    <th>Date</th>
                    <th>Duration</th>
                </tr>
        """
        for test in tests:
            if test['status'] == 'PASS':
                status_class = "pass"
            elif test['status'] == 'SKIP':
                status_class = "skip"
            else:
                status_class = "fail"

            details_html = ""
            if test['status'] != 'PASS' and test['message']:
                # For SKIPS, show fixed text. For FAIL, show collapsible error.
                if test['status'] == 'SKIP':
                    details_html = f'<span style="color: #666; font-size: 0.9em;">{test["message"]}</span>'
                else:
                    details_html = f"""
                    <details>
                        <summary style="cursor: pointer; color: blue;">View Error</summary>
                        <div style="background-color: #f8f8f8; padding: 5px; border: 1px solid #ddd; font-size: 0.9em; white-space: pre-wrap;">{test['message']}</div>
                    </details>
                    """
            
            exec_date = format_date_display(test['end_time'])
            duration_str = format_duration(test['elapsed_time'])
            bar_color = "#00a651" if test['status'] == 'PASS' else "#ff0000"
            status_bar = f'<span style="display: inline-block; width: 60px; height: 12px; background-color: {bar_color}; border-radius: 999px; vertical-align: middle; margin-left: 10px;"></span>'

            table_html += f"""
                <tr>
                    <td>{test['id']}</td>
                    <td>{test['name']}</td>
                    <td class="{status_class}">{test['status']} {status_bar}</td>
                    <td>{details_html}</td>
                    <td>{exec_date}</td>
                    <td>{duration_str}</td>
                </tr>
            """
        table_html += "</table></details><br>"
        return table_html

    for cat in sorted_categories:
        html += render_table(tests_by_category[cat], cat.capitalize())

    html += "</body></html>"
    return html

def send_email(subject, body, report_dir, results_dir, smtp_config):
    msg = MIMEMultipart()
    msg['From'] = smtp_config['sender']
    msg['To'] = smtp_config['recipient']
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    # Attach Chart as Inline Image
    chart_path = os.path.join(report_dir, 'summary_chart.png')
    if os.path.exists(chart_path):
        with open(chart_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<summary_chart>')
            msg.attach(img)
    
    # Attach evidence files
    base_video_dir = os.path.join(results_dir, 'video')
    files_to_attach = []
    
    if os.path.exists(base_video_dir):
        for root, dirs, files in os.walk(base_video_dir):
            for file in files:
                if file.endswith('.webm') or file.endswith('.html'):
                    files_to_attach.append(os.path.join(root, file))

    for file_path in files_to_attach:
         # Limit attachment size logic could go here
        with open(file_path, 'rb') as f:
            filename = os.path.basename(file_path)
            part = MIMEApplication(f.read(), Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

    try:
        host = smtp_config.get('server')
        port = int(smtp_config.get('port', 25))
        user = smtp_config.get('user')
        password = smtp_config.get('password')

        if not host: 
            print("SMTP host not provided. Skipping email.")
            return

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def run_report(results_dir, history_file='execution_history.json', report_dir='report', smtp_config=None, requested_tags=None):
    """
    Main entry point for generating report.
    results_dir: Path to directory containing output.xml and browser results (e.g. 'results')
    """
    # 🔗 Fallback to environment variable if not provided
    requested_tags = requested_tags or os.getenv('REQUESTED_TAGS')

    output_xml = os.path.join(results_dir, 'output.xml')
    history_path = os.path.join(results_dir, history_file)
    report_path = os.path.join(results_dir, report_dir) # report inside results usually

    if not os.path.exists(output_xml):
        print(f"Error: '{output_xml}' not found.")
        return

    result = ExecutionResult(output_xml)
    metrics = TestMetrics()
    result.visit(metrics)

    # 🕵️ Synthetic Skip Logic: Apply before evidence and chart
    metrics.apply_synthetic_skips(requested_tags)

    history = load_history(history_path)
    updated_history = manage_evidence(metrics.tests, history, results_dir)
    save_history(updated_history, history_path)

    chart_path = generate_chart(metrics, report_path)
    html_body = generate_html_report_body(metrics, chart_path, history, report_path)

    if smtp_config:
        send_email("Daily Test Report", html_body, report_path, results_dir, smtp_config)
    else:
        print("SMTP config missing or empty. Skipping email.")
