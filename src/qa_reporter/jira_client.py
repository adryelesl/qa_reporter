import os
import requests
import json
import re
from datetime import datetime
from robot.api import ExecutionResult
from .metrics import TestMetrics

def get_field_id_by_name(jira_config, field_name):
    domain = jira_config.get('domain')
    email = jira_config.get('email')
    token = jira_config.get('token')

    if not domain or not token:
         return None

    # Clean domain just in case
    clean_domain = domain.replace('https://', '').replace('http://', '').split('/')[0].strip()
    
    url = f"https://{clean_domain}/rest/api/3/field"
    auth = (email, token)
    headers = {"Accept": "application/json"}
    
    try:
        response = requests.get(url, auth=auth, headers=headers)
        if response.status_code != 200:
            print(f"⚠️ Failed to fetch fields: {response.status_code} - {response.text}")
            print("🔄 Retrying with API v2...")
            url_v2 = f"https://{clean_domain}/rest/api/2/field"
            response = requests.get(url_v2, auth=auth, headers=headers)
            
            if response.status_code != 200:
                 print(f"⚠️ Failed to fetch fields (v2): {response.status_code} - {response.text}")
                 return None
            
        fields = response.json()
        for field in fields:
            if 'name' in field and field['name'].lower() == field_name.lower():
                return field['id']
    except Exception as e:
        print(f"⚠️ Error fetching fields: {e}")
        
    return None

def format_duration(ms):
    seconds = int(ms / 1000)
    m, s = divmod(seconds, 60)
    return f"{m}m {s}s"

def build_adf_content(metrics, duration_str, start_time, chart_url=None):
    status_text = "✅ PASSED" if metrics.failed == 0 else "❌ FAILED"
    environment_str = ", ".join(metrics.categories) if metrics.categories else "General"
    
    content = [
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "🚀 Execution Report"}]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Global Status: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": f"{status_text} "},
            ]
        },
         {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Environment: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": f"{environment_str}"},
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Execution Date: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": f"{start_time}"},
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Total Duration: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": f"{duration_str}"},
            ]
        }
    ]
    
    if chart_url:
        content.append({
            "type": "mediaSingle",
            "attrs": {
                "layout": "align-start",
                "width": 60 
            },
            "content": [
                {
                    "type": "media",
                    "attrs": {
                        "type": "external",
                        "url": chart_url
                    }
                }
            ]
        })
    
    content.append({
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default", "width": 300},
        "content": [
            {
                "type": "tableRow",
                "content": [
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Total"}]}]},
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pass"}]}]},
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fail"}]}]},
                ]
            },
            {
                "type": "tableRow",
                "content": [
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(metrics.total)}]}]},
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(metrics.passed), "marks": [{"type": "textColor", "attrs": {"color": "#006644"}}]}]}]},
                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(metrics.failed), "marks": [{"type": "textColor", "attrs": {"color": "#BF2600"}}]}]}]},
                ]
            }
        ]
    })
    
    content.append({
        "type": "heading",
        "attrs": {"level": 4},
        "content": [{"type": "text", "text": "📄 Detailed Results"}]
    })
    
    # Group tests by category
    grouped_tests = {}
    for test in metrics.tests:
        cat = test.get('category', 'Uncategorized')
        if cat not in grouped_tests:
            grouped_tests[cat] = []
        grouped_tests[cat].append(test)
    
    # Sort categories to keep Frontend/Backend order consistent if possible
    sorted_categories = sorted(grouped_tests.keys())
    
    for cat in sorted_categories:
        tests = grouped_tests[cat]
        
        # Add Category Heading
        content.append({
            "type": "heading",
            "attrs": {"level": 5},
            "content": [{"type": "text", "text": f"{cat.capitalize()} ({len(tests)})"}]
        })

        table_rows = [
            {
                "type": "tableRow",
                "content": [
                     {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test ID"}]}]},
                     {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Name"}]}]},
                     {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
                     {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Details"}]}]},
                     {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Duration"}]}]}
                ]
            }
        ]
        
        for test in tests:
            # Status styling
            if test['status'] == 'PASS':
                status_color = "#006644"
                status_icon = "PASS"
            elif test['status'] == 'SKIP':
                status_color = "#707070" # Gray for skipped
                status_icon = "SKIP"
            else:
                status_color = "#BF2600"
                status_icon = "FAIL"
            
            # Details: Show error message if not passed, checkmark if passed
            detail_text = test.get('message', '') if test['status'] != 'PASS' else "✓"
            if not detail_text and test['status'] != 'PASS':
                 detail_text = "No details provided"

            table_rows.append({
                "type": "tableRow",
                "content": [
                     {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": test['id']}]}]},
                     {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": test['name']}]}]},
                     {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": status_icon, "marks": [{"type": "textColor", "attrs": {"color": status_color}}, {"type": "strong"}]}]}]},
                     {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": detail_text}]}]},
                     {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": format_duration(test['duration'])}]}]}
                ]
            })
            
        content.append({
            "type": "table",
            "attrs": {"isNumberColumnEnabled": False, "layout": "wide"},
            "content": table_rows
        })
    
    content.append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "ℹ️ Note: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": "Please check the issue attachments for "},
                {"type": "text", "text": "Videos", "marks": [{"type": "strong"}]},
                {"type": "text", "text": " and "},
                {"type": "text", "text": "HTML Logs", "marks": [{"type": "strong"}]},
                {"type": "text", "text": "."}
            ]
    })
        
    return {
        "version": 1,
        "type": "doc",
        "content": content
    }

def update_jira_issue(jira_config, field_id, adf_body, retry_without_media=False):
    domain = jira_config.get('domain')
    clean_domain = domain.replace('https://', '').replace('http://', '').split('/')[0].strip()
    issue_key = jira_config.get('issue_key')
    email = jira_config.get('email')
    token = jira_config.get('token')
    
    url = f"https://{clean_domain}/rest/api/3/issue/{issue_key}"
    auth = (email, token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": {
            field_id: adf_body
        }
    }
    
    response = requests.put(url, json=payload, auth=auth, headers=headers)
    
    if response.status_code == 204:
        print(f"✅ Successfully updated field '{field_id}' in {issue_key}")
        return True
    elif response.status_code == 400 and not retry_without_media:
        print(f"⚠️ 400 Error updating issue (Likely due to Attachment/Media). Details: {response.text}")
        print("🔄 Retrying without Chart...")
        return False
    else:
        print(f"⚠️ Failed to update issue: {response.status_code} - {response.text}")
        return False

def upload_file(jira_config, file_path):
    domain = jira_config.get('domain')
    clean_domain = domain.replace('https://', '').replace('http://', '').split('/')[0].strip()
    issue_key = jira_config.get('issue_key')
    email = jira_config.get('email')
    token = jira_config.get('token')

    url = f"https://{clean_domain}/rest/api/3/issue/{issue_key}/attachments"
    auth = (email, token)
    headers = {"X-Atlassian-Token": "no-check"}
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, auth=auth, headers=headers)
            if response.status_code == 200:
                print(f"✅ Uploaded {os.path.basename(file_path)}")
                data = response.json()
                if data and len(data) > 0 and 'id' in data[0]:
                    return data[0]['id'], data[0].get('content', '')
            else:
                print(f"⚠️ Failed to upload {os.path.basename(file_path)}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error uploading {file_path}: {e}")
        
    return None, None

def upload_evidence_files(jira_config, executed_test_ids, video_dir):
    if not os.path.exists(video_dir):
        return

    files_to_upload = []
    print(f"🔍 Filtering evidence for tests: {executed_test_ids}")
    
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            if file.endswith('.webm') or file.endswith('.png'):
                is_relevant = False
                for t_id in executed_test_ids:
                    if file.startswith(t_id):
                        is_relevant = True
                        break
                
                if is_relevant:
                    files_to_upload.append(os.path.join(root, file))
    
    if not files_to_upload:
        print("ℹ️ No relevant evidence files found.")
        return
        
    print(f"📎 Uploading {len(files_to_upload)} evidence files...")
    for file_path in files_to_upload:
        upload_file(jira_config, file_path)

def add_jira_comment(jira_config, adf_body, retry_without_media=False):
    domain = jira_config.get('domain')
    clean_domain = domain.replace('https://', '').replace('http://', '').split('/')[0].strip()
    issue_key = jira_config.get('issue_key')
    email = jira_config.get('email')
    token = jira_config.get('token')
    
    url = f"https://{clean_domain}/rest/api/3/issue/{issue_key}/comment"
    auth = (email, token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "body": adf_body
    }
    
    response = requests.post(url, json=payload, auth=auth, headers=headers)
    
    if response.status_code == 201:
        print(f"✅ Successfully added comment to {issue_key}")
        return True
    elif response.status_code == 400 and not retry_without_media:
        print(f"⚠️ 400 Error adding comment. Details: {response.text}")
        return False
    else:
        print(f"⚠️ Failed to add comment: {response.status_code} - {response.text}")
        return False

def sync_to_jira(jira_config, results_dir, output_xml_path='output.xml', chart_path='report/summary_chart.png', video_dir='video', custom_field_name='Last Execution', requested_tags=None):
    """
    Main entry point for Jira Sync.
    jira_config: dict with keys 'domain', 'email', 'token', 'issue_key'
    results_dir: base results directory
    output_xml_path: relative path to output.xml from results_dir
    chart_path: relative path to chart from results_dir
    video_dir: relative path to video dir from results_dir
    requested_tags: raw string of tags requested (e.g. from GitHub inputs)
    """
    
    # Construct full paths
    full_output_xml = os.path.join(results_dir, output_xml_path)
    full_chart_path = os.path.join(results_dir, chart_path)
    full_video_dir = os.path.join(results_dir, video_dir)
    
    # 🔗 Fallback to environment variable if not provided
    requested_tags = requested_tags or os.getenv('REQUESTED_TAGS')

    if not all(jira_config.values()):
        print("⚠️ Missing Jira Configuration. Skipping Jira Sync.")
        return

    metrics = TestMetrics()
    executed_ids = []
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if os.path.exists(full_output_xml):
        result = ExecutionResult(full_output_xml)
        result.visit(metrics)
        executed_ids = [t['id'] for t in metrics.tests]
        try:
            start_time_raw = result.suite.starttime
            start_time = datetime.strptime(start_time_raw, '%Y%m%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
    else:
        print(f"⚠️ Warning: '{full_output_xml}' not found. Syncing skips only.")
    
    # 🕵️ Synthetic Skip Logic: Use centralized method
    metrics.apply_synthetic_skips(requested_tags)

    chart_id = None
    chart_url = None
    if os.path.exists(full_chart_path):
        print("📊 Uploading Chart to get ID...")
        chart_id, chart_url = upload_file(jira_config, full_chart_path)

    print(f"🔍 Searching for field ID for '{custom_field_name}'...")
    field_id = get_field_id_by_name(jira_config, custom_field_name)
    
    duration_str = format_duration(metrics.duration)
    adf_content = build_adf_content(metrics, duration_str, start_time, chart_url)

    if not field_id:
        print(f"ℹ️ Could not find field with name '{custom_field_name}'. Overwriting the ticket Description instead...")
        field_id = "description"
        
    print(f"✅ Updating Field ID: {field_id}")
    
    success = update_jira_issue(jira_config, field_id, adf_content)
    
    if not success and chart_url:
        print("🔄 Retrying update without chart link...")
        adf_content_fallback = build_adf_content(metrics, duration_str, start_time, None)
        update_jira_issue(jira_config, field_id, adf_content_fallback, retry_without_media=True)
    
    upload_evidence_files(jira_config, executed_ids, full_video_dir)
    
    # Upload main Robot Framework result files
    main_files = ['log.html', 'report.html', 'output.xml']
    for file_name in main_files:
        file_path = os.path.join(results_dir, file_name)
        if os.path.exists(file_path):
            print(f"📄 Uploading main file: {file_name}...")
            upload_file(jira_config, file_path)
