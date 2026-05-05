# Create this file: create_test_pdf.py

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Content
title = "COMPANY REMOTE WORK GUIDELINES"
content = """
1. REMOTE WORK EQUIPMENT
All remote employees receive company laptop, docking station, keyboard, mouse, headset, and optional second monitor.

2. INTERNET REIMBURSEMENT
Company reimburses up to $50/month for home internet. Submit receipts to finance@company.com by the 5th.

3. HOME OFFICE SETUP
Requirements: Dedicated workspace, ergonomic chair ($300 allowance), good lighting, quiet environment.

4. WORKING HOURS
Flexible start (8-10 AM), core hours (10 AM-3 PM), flexible end (4-7 PM). Total 8 hours/day.

5. COMMUNICATION TOOLS
Slack (15 min response), Zoom (camera on), Email (24h response), JIRA (task tracking).

6. SECURITY REQUIREMENTS
Use VPN, lock computer when away, no public WiFi, monthly security training.

7. PERFORMANCE EXPECTATIONS
Daily standup 10 AM, weekly 1-on-1, Friday timesheet, meet deadlines.

8. ELIGIBILITY
After 6 months, manager approval, security training, home office inspection.
"""

# Create PDF
pdf = SimpleDocTemplate("knowledge_base/general/Remote_Work_Guidelines.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add title
story.append(Paragraph(title, styles['Title']))
story.append(Spacer(1, 12))

# Add content
for line in content.split('\n'):
    if line.strip():
        story.append(Paragraph(line, styles['BodyText']))
        story.append(Spacer(1, 6))

# Build PDF
pdf.build(story)
print("✅ PDF created: knowledge_base/general/Remote_Work_Guidelines.pdf")
