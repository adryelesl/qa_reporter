from robot.api import ResultVisitor
from datetime import datetime

class TestMetrics(ResultVisitor):
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.duration = 0 # Specifically for Jira duration sum
        self.tests = []
        self.categories = set()

    def visit_test(self, test):
        self.total += 1
        elapsed_time = test.elapsedtime if hasattr(test, 'elapsedtime') else 0
        self.duration += elapsed_time

        if test.status == 'PASS':
            self.passed += 1
        elif test.status == 'FAIL':
            self.failed += 1
        else:
            self.skipped += 1
        
        # Tags logic
        test_id = test.name
        category = 'Uncategorized'
        
        if test.tags:
            for tag in test.tags:
                if tag.startswith('T') and tag[1:].isdigit():
                    test_id = tag
                if tag.lower() in ['frontend', 'backend', 'api', 'ui', 'e2e']:
                    category = tag.lower()
        
        if test_id == test.name and test.tags:
            # Fallback if no Txxx
             test_id = test.tags[0] 
        
        self.categories.add(category)

        # Collect messages
        messages = []
        def collect_messages(item):
            if hasattr(item, 'messages'):
                for msg in item.messages:
                    messages.append(msg.message)
            if hasattr(item, 'setup') and item.setup:
                collect_messages(item.setup)
            if hasattr(item, 'body'):
                for child in item.body:
                    collect_messages(child)
            if hasattr(item, 'teardown') and item.teardown:
                collect_messages(item.teardown)
        
        collect_messages(test)
        
        end_time = test.endtime if hasattr(test, 'endtime') else datetime.now().strftime('%Y%m%d %H:%M:%S.%f')
        
        self.tests.append({
            'name': test.name,
            'id': test_id,
            'tags': list(test.tags),
            'status': test.status,
            'message': test.message,
            'messages': messages,
            'category': category,
            'elapsed_time': elapsed_time, # in ms
            'duration': elapsed_time,    # Alias for clarity
            'end_time': end_time
        })

    def apply_synthetic_skips(self, requested_tags):
        """
        Detects T-IDs requested but not found in execution results and adds them as SKIPPED.
        """
        if not requested_tags:
            return

        import re
        executed_ids = [t['id'] for t in self.tests]
        
        # Resolve major category from tags to assign to the skipped tests
        major_categories = ['frontend', 'backend', 'api', 'ui', 'e2e']
        active_cat = 'Uncategorized'
        for tag in requested_tags.split():
            if tag.lower() in major_categories:
                active_cat = tag.lower()

        # Find all Txxx patterns in requested tags
        requested_ids = re.findall(r'T\d+', requested_tags, re.I)
        
        for req_id in requested_ids:
            if req_id not in executed_ids:
                # Add to report as skipped
                self.tests.append({
                    'id': req_id,
                    'name': 'Filtered Out / Not Found',
                    'status': 'SKIP',
                    'message': f'Test was requested in tags but did not match filter (likely not {active_cat})',
                    'category': active_cat,
                    'messages': [],
                    'elapsed_time': 0,
                    'duration': 0,
                    'end_time': datetime.now().strftime('%Y%m%d %H:%M:%S.%f'),
                    'tags': [active_cat, req_id]
                })
                self.total += 1
                self.skipped += 1
                self.categories.add(active_cat)
