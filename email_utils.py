# email_utils.py
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import time
from datetime import datetime, timedelta
import re

# ============================================
# EMAIL FETCHING (GMAIL IMAP)
# ============================================

class EmailFetcher:
    def __init__(self, email_address, app_password):
        """
        Initialize with Gmail credentials
        App password is needed, not regular password
        """
        self.email = email_address
        self.password = app_password
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
    def fetch_recent_emails(self, hours=1, max_emails=20):
        """
        Fetch emails from last X hours
        Returns list of email dictionaries
        """
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select("inbox")
            
            # Calculate date for filtering
            since_date = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")
            
            # Search for emails from last X hours
            result, data = mail.search(None, f'(SINCE "{since_date}")')
            
            emails = []
            for num in data[0].split()[-max_emails:]:  # Get last max_emails
                result, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extract email details
                email_data = self._parse_email(msg)
                emails.append(email_data)
            
            mail.close()
            mail.logout()
            return emails
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _parse_email(self, msg):
        """Parse email message into dictionary"""
        # Get subject
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else "utf-8")
        
        # Get from
        from_addr = msg.get("From")
        
        # Get date
        date = msg.get("Date")
        
        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        
        return {
            "subject": subject,
            "from": from_addr,
            "date": date,
            "body": body[:1000],  # Limit body length
            "full_body": body
        }
    
    def send_email(self, to_email, subject, body):
        """Send an email using SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

# ============================================
# URGENT EMAIL DETECTION
# ============================================

def detect_urgent_emails(emails):
    """
    Analyze emails and mark urgent ones
    Returns list of urgent emails with reasons
    """
    urgent_keywords = [
        "urgent", "asap", "deadline", "due", "important", 
        "action required", "immediate", "critical", "emergency",
        "overdue", "expiring", "today", "tomorrow"
    ]
    
    urgent_emails = []
    
    for email_data in emails:
        reasons = []
        content = (email_data["subject"] + " " + email_data["body"]).lower()
        
        # Check for urgent keywords
        for keyword in urgent_keywords:
            if keyword in content:
                reasons.append(f"Contains '{keyword}'")
        
        # Check for deadlines (simple regex for dates)
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 12/25/2024
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}',
            r'tomorrow|today|next week|by friday'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                reasons.append("Contains date/deadline")
                break
        
        # If urgent, add to list
        if reasons:
            urgent_emails.append({
                **email_data,
                "urgency_reasons": reasons
            })
    
    return urgent_emails


# ============================================
# WHATSAPP ALERTS (using WhatsApp API or webhook)
# ============================================

class WhatsAppNotifier:
    def __init__(self, phone_number):
        """
        Initialize with phone number
        Note: You'll need a WhatsApp Business API or service like Twilio
        For demo, we'll use a mock or a simple webhook
        """
        self.phone = phone_number
        
        # Option 1: Use a free service like CallMeBot
        # (works for WhatsApp but requires opt-in)
        self.use_callmebot = True
        
    def send_alert(self, message):
        """Send WhatsApp alert"""
        if self.use_callmebot:
            return self._send_via_callmebot(message)
        else:
            print(f"[MOCK] WhatsApp alert to {self.phone}: {message}")
            return True
    
    def _send_via_callmebot(self, message):
        """
        Send via CallMeBot (free but requires user to opt-in)
        User must save this number: +34 644 53 99 18
        and send message: "I allow callmebot to send me messages"
        """
        try:
            # Encode message for URL
            import urllib.parse
            encoded_msg = urllib.parse.quote(message)
            
            # CallMeBot API
            url = f"https://api.callmebot.com/whatsapp.php?phone={self.phone}&text={encoded_msg}&apikey=12345"
            
            response = requests.get(url)
            return response.status_code == 200
        except Exception as e:
            print(f"WhatsApp send error: {e}")
            return False


# ============================================
# EMAIL COMPOSITION (mailto: links)
# ============================================

def create_mailto_link(to_email, subject, body):
    """
    Create a mailto link that opens user's email client
    """
    import urllib.parse
    
    # Encode subject and body for URL
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body)
    
    mailto = f"mailto:{to_email}?subject={encoded_subject}&body={encoded_body}"
    return mailto


def format_email_body(content, sender_name="", recipient_name=""):
    """
    Format email body professionally
    """
    lines = []
    
    # Add greeting
    if recipient_name:
        lines.append(f"Dear {recipient_name},")
    else:
        lines.append("Dear Sir/Madam,")
    
    lines.append("")
    lines.append(content)
    lines.append("")
    
    # Add signature
    if sender_name:
        lines.append(f"Best regards,")
        lines.append(sender_name)
    else:
        lines.append("Best regards,")
        lines.append("[Your Name]")
    
    return "\n".join(lines)


# ============================================
# EMAIL SUMMARIZER (uses AI)
# ============================================

def summarize_emails_with_ai(emails, urgent_emails):
    """
    Create a summary of emails using AI
    This will be called from app.py
    """
    summary_parts = []
    
    # Urgent alerts section
    if urgent_emails:
        summary_parts.append("🔴 **URGENT ALERTS**")
        for i, email in enumerate(urgent_emails[:5], 1):
            summary_parts.append(f"{i}. **{email['subject']}**")
            summary_parts.append(f"   From: {email['from']}")
            summary_parts.append(f"   Urgent because: {', '.join(email['urgency_reasons'])}")
        summary_parts.append("")
    
    # Email summaries
    summary_parts.append("📧 **Email Summary**")
    for i, email in enumerate(emails[:10], 1):
        # Truncate subject if too long
        subject = email['subject'][:50] + "..." if len(email['subject']) > 50 else email['subject']
        summary_parts.append(f"{i}. {subject}")
        summary_parts.append(f"   From: {email['from']}")
        
        # Add a brief preview
        preview = email['body'][:100].replace('\n', ' ') + "..."
        summary_parts.append(f"   Preview: {preview}")
        summary_parts.append("")
    
    return "\n".join(summary_parts)


# ============================================
# CONFIGURATION STORAGE (simple JSON file)
# ============================================

import json
import os

CONFIG_FILE = "email_config.json"

def save_config(email, app_password, phone):
    """Save user configuration"""
    config = {
        "email": email,
        "app_password": app_password,  # In production, encrypt this!
        "phone": phone,
        "connected": True,
        "last_checked": datetime.now().isoformat()
    }
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    
    return config

def load_config():
    """Load user configuration"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def clear_config():
    """Clear configuration (disconnect)"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)