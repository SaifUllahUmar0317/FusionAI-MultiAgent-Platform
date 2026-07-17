from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from flask_cors import CORS
import speech_recognition as sr
from datetime import datetime, timedelta
from fusionai import fusionai
import tempfile
import requests
import json
import re
import os
from word_generator_agent import create_word_document_bytes, parse_user_request

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)

# Updated CORS configuration (combined both versions)
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:3000"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"])

# ===============================
# GitHub OAuth Configuration
# ===============================
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:5000/github/callback")

# ===============================
# Word Generator Configuration
# ===============================
WORD_GENERATOR_URL = "http://localhost:8000"

# ===============================
# Main Routes
# ===============================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html")

@app.route("/sign_up")
def sign_up():
    return render_template("sign_up.html")

# ===============================
# Chat & AI Routes
# ===============================

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_text = data.get("message", "")
        agent = data.get("agent", "groq")

        print("\n" + "="*50)
        print(f"🔵 CHAT REQUEST RECEIVED")
        print(f"📝 User text: '{user_text}'")
        print(f"🤖 Agent: '{agent}'")
        print(f"📊 Multi mode: {agent == 'multibot'}")

        # Decide multi mode
        multi_mode = True if agent == "multibot" else False

        # Initialize history
        if 'history' not in session:
            session['history'] = []
            print("🆕 New session created")

        print(f"📚 History length: {len(session['history'])}")
        if session['history']:
            print(f"📖 Last message: {session['history'][-1]}")

        # Call fusionai with try-except to catch specific errors
        print("🔄 Calling fusionai()...")
        try:
            reply = fusionai(user_text, session['history'], multi=multi_mode)
            print(f"✅ fusionai() returned successfully")
            print(f"💬 Reply preview: {reply[:100]}...")
        except Exception as e:
            print(f"❌❌❌ ERROR in fusionai(): {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"AI processing failed: {str(e)}"}), 500
        
        try:
            # Save to conversations.json
            conversation = {
                'timestamp': datetime.now().isoformat(),
                'agent': agent,
                'user_message': user_text,
                'ai_response': reply
            }
            
            # Create database directory if it doesn't exist
            os.makedirs('database', exist_ok=True)
            
            # Load existing conversations
            history_file = 'database/conversations.json'
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add new conversation
            history.append(conversation)
            
            # Keep only last 1000 conversations to prevent file from getting too big
            if len(history) > 1000:
                history = history[-1000:]
            
            # Save back to file
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            print(f"✅ Conversation saved to database")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save conversation: {e}")

        # Update history
        session['history'].append({"role": "user", "content": user_text})
        session['history'].append({"role": "assistant", "content": reply})
        session['history'] = session['history'][-10:]
        session.modified = True

        print("✅ Chat request completed successfully")
        print("="*50 + "\n")

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"💥 UNHANDLED ERROR in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/voice-to-text", methods=["POST"])
def voice_to_text():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return jsonify({"transcribed_text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===============================
# File Analysis Routes
# ===============================

@app.route("/analyze-file", methods=["POST"])
def analyze_file():
    file = request.files.get("file")
    context = request.form.get("context", "")

    if not file:
        return jsonify({"reply": "No file received."})

    filename = file.filename
    file_size = len(file.read())
    file.seek(0)
    file_ext = os.path.splitext(filename)[1].lower()

    # Basic response based on file type
    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        reply = f"📸 I received your image: {filename} ({file_size} bytes)"
    elif file_ext in ['.pdf']:
        reply = f"📄 I received your PDF: {filename} ({file_size} bytes)"
    elif file_ext in ['.doc', '.docx']:
        reply = f"📝 I received your Word document: {filename} ({file_size} bytes)"
    elif file_ext in ['.xls', '.xlsx']:
        reply = f"📊 I received your Excel file: {filename} ({file_size} bytes)"
    elif file_ext in ['.txt', '.md']:
        try:
            content = file.read().decode('utf-8')[:500]
            reply = f"📄 I received your text file: {filename}\n\nPreview:\n{content}..."
        except:
            reply = f"📄 I received your text file: {filename}"
    else:
        reply = f"📎 I received your file: {filename} ({file_size} bytes)"

    if context:
        reply += f"\n\n📝 Your instructions: {context}\n\nI'll process this accordingly. (File analysis feature can be expanded based on your needs.)"
    else:
        reply += "\n\nWhat would you like me to do with this file? You can add context by clicking the file badge above."

    return jsonify({"reply": reply})

@app.route("/analyze-multiple-files", methods=["POST"])
def analyze_multiple_files():
    file_count = int(request.form.get('file_count', 0))
    context = request.form.get('context', '')

    files_info = []
    for i in range(file_count):
        file = request.files.get(f'file{i}')
        if file:
            filename = file.filename
            file_size = len(file.read())
            file.seek(0)
            files_info.append(f"{filename} ({file_size} bytes)")

    if not files_info:
        return jsonify({"reply": "No files received."})

    reply = f"📎 Received {len(files_info)} file(s):\n\n"
    for info in files_info:
        reply += f"• {info}\n"

    if context:
        reply += f"\n\n📝 Your instructions: {context}"
    else:
        reply += "\n\nWhat would you like me to do with these files?"

    return jsonify({"reply": reply})

# ===============================
# GitHub OAuth Routes
# ===============================

@app.route('/github/login')
def github_login():
    return redirect(f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_REDIRECT_URI}&scope=repo,user")

@app.route('/github/callback')
def github_callback():
    code = request.args.get('code')

    response = requests.post(
        'https://github.com/login/oauth/access_token',
        headers={'Accept': 'application/json'},
        data={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code
        }
    )

    token_data = response.json()
    access_token = token_data.get('access_token')

    if access_token:
        session['github_token'] = access_token
        return redirect('/')
    else:
        return "GitHub authentication failed", 400

@app.route('/github/disconnect', methods=['POST'])
def github_disconnect():
    session.pop('github_token', None)
    return jsonify({"success": True})

@app.route('/github/status')
def github_status():
    token = session.get('github_token')
    if not token:
        return jsonify({"connected": False})

    response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {token}'}
    )

    if response.status_code == 200:
        user_data = response.json()
        return jsonify({
            "connected": True,
            "username": user_data.get('login')
        })
    else:
        return jsonify({"connected": False})

# ===============================
# GitHub Search Routes
# ===============================

@app.route('/github/search/repos')
def github_search_repos():
    query = request.args.get('q', '')
    token = session.get('github_token')

    if not token:
        return jsonify({"error": "Not connected to GitHub"}), 401

    search_query = query
    language = request.args.get('language', '')
    if language:
        search_query += f"+language:{language}"

    min_stars = request.args.get('min_stars', '')
    if min_stars:
        search_query += f"+stars:>={min_stars}"

    response = requests.get(
        f'https://api.github.com/search/repositories?q={search_query}&sort=stars&order=desc&per_page=10',
        headers={'Authorization': f'token {token}'}
    )

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Search failed", "details": response.text}), response.status_code

@app.route('/github/search/code')
def github_search_code():
    query = request.args.get('q', '')
    repo = request.args.get('repo', '')
    token = session.get('github_token')

    if not token:
        return jsonify({"error": "Not connected to GitHub"}), 401

    search_query = query
    if repo:
        search_query += f"+repo:{repo}"

    response = requests.get(
        f'https://api.github.com/search/code?q={search_query}&per_page=10',
        headers={'Authorization': f'token {token}'}
    )

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Search failed", "details": response.text}), response.status_code

@app.route('/github/repo/contents')
def github_repo_contents():
    repo = request.args.get('repo', '')
    path = request.args.get('path', '')
    token = session.get('github_token')

    if not token:
        return jsonify({"error": "Not connected to GitHub"}), 401
    if not repo:
        return jsonify({"error": "Repository required"}), 400

    path = path.strip('/')

    response = requests.get(
        f'https://api.github.com/repos/{repo}/contents/{path}',
        headers={'Authorization': f'token {token}'}
    )

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to get contents", "details": response.text}), response.status_code

@app.route('/github/repo/readme')
def github_repo_readme():
    repo = request.args.get('repo', '')
    token = session.get('github_token')

    if not token:
        return jsonify({"error": "Not connected to GitHub"}), 401

    if not repo:
        return jsonify({"error": "Repository required"}), 400

    response = requests.get(
        f'https://api.github.com/repos/{repo}/readme',
        headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3.html+json'
        }
    )

    if response.status_code == 200:
        return jsonify({"content": response.text})
    else:
        return jsonify({"error": "Failed to get README", "details": response.text}), response.status_code

@app.route('/github/repo/commits')
def github_repo_commits():
    repo = request.args.get('repo', '')
    path = request.args.get('path', '')
    token = session.get('github_token')

    if not token:
        return jsonify({"error": "Not connected to GitHub"}), 401
    if not repo:
        return jsonify({"error": "Repository required"}), 400

    url = f'https://api.github.com/repos/{repo}/commits'
    if path:
        url += f'?path={path}'

    response = requests.get(
        url,
        headers={'Authorization': f'token {token}'}
    )

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to get commits", "details": response.text}), response.status_code

# ===============================
# Word Generator Route
# ===============================

@app.route("/generate-word", methods=["POST"])
def generate_word_document():
    data = request.json
    user_input = data.get("message", "")
    
    print(f"📝 User input: {user_input}")
    
    # Just pass the raw user input to FastAPI - let it handle all parsing
    word_request = {
        "user_input": user_input,
        "topic": "",  # Empty, FastAPI will extract
        "pages": 1,   # Default, FastAPI will override
        "font_name": "Times New Roman",  # Default, FastAPI will override
        "font_size": 12,  # Default, FastAPI will override
        "font_color": [0, 0, 0],  # Default black
        "font_color_name": None,
        "content": None
    }
    
    print(f"📤 Sending raw input to FastAPI: {user_input[:100]}...")
    
    try:
        response = requests.post(
            f"{WORD_GENERATOR_URL}/generate-word",
            json=word_request,
            timeout=180
        )
        
        if response.status_code == 200:
            content_disposition = response.headers.get('Content-Disposition', 'attachment; filename="document.docx"')
            return response.content, 200, {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'Content-Disposition': content_disposition
            }
        else:
            try:
                doc_bytes, download_name = create_word_document_bytes(user_input)
                return doc_bytes, 200, {
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'Content-Disposition': f'attachment; filename="{download_name}"'
                }
            except Exception as local_error:
                error_detail = response.json() if response.content else {"error": "Unknown error"}
                return jsonify({
                    "error": f"Word generation failed: {error_detail.get('detail', 'Unknown error')} | Local fallback failed: {local_error}"
                }), 500
    except requests.exceptions.ConnectionError:
        try:
            doc_bytes, download_name = create_word_document_bytes(user_input)
            return doc_bytes, 200, {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'Content-Disposition': f'attachment; filename="{download_name}"'
            }
        except Exception as local_error:
            return jsonify({
                "error": f"Word Generator service not running. Local fallback failed: {local_error}"
            }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/parse-word-request", methods=["POST"])
def parse_word_request_endpoint():
    data = request.json
    user_input = data.get("message", "")

    word_request = {
        "user_input": user_input,
        "topic": "Document",
        "pages": 1,
        "font_name": "Times New Roman",
        "font_size": 12,
        "font_color": [0, 0, 0],
        "font_color_name": None,
        "content": None
    }

    try:
        response = requests.post(
            f"{WORD_GENERATOR_URL}/parse-word-request",
            json=word_request,
            timeout=30
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"⚠️ Parse service returned status {response.status_code}: {response.text}")
            return jsonify(parse_user_request(user_input))
    except Exception as e:
        print(f"Error parsing request: {e}")
        return jsonify(parse_user_request(user_input))

# ===============================
# Auth Routes
# ===============================

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    # Add your database logic here
    return jsonify({"success": True, "message": "Account created successfully"})

# ===============================
# Dashboard
# ===============================

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# ===============================
# Email Pro Routes
# ===============================

from email_utils import (
    EmailFetcher, detect_urgent_emails, WhatsAppNotifier,
    summarize_emails_with_ai, create_mailto_link, format_email_body,
    save_config, load_config, clear_config
)

@app.route("/email/connect", methods=["POST"])
def email_connect():
    """Save email and WhatsApp configuration"""
    try:
        data = request.json
        email = data.get("email")
        app_password = data.get("app_password")
        phone = data.get("phone")
        
        # Save configuration
        config = save_config(email, app_password, phone)
        
        # Test connection
        fetcher = EmailFetcher(email, app_password)
        test_emails = fetcher.fetch_recent_emails(hours=1, max_emails=1)
        
        if test_emails is not None:
            return jsonify({"success": True, "message": "Connected successfully!"})
        else:
            return jsonify({"success": False, "error": "Failed to connect to email"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/email/status", methods=["GET"])
def email_status():
    """Check if email is connected"""
    config = load_config()
    if config:
        return jsonify({
            "connected": True,
            "email": config.get("email"),
            "phone": config.get("phone")
        })
    return jsonify({"connected": False})


@app.route("/email/disconnect", methods=["POST"])
def email_disconnect():
    """Disconnect email"""
    clear_config()
    return jsonify({"success": True})


@app.route("/email/summarize-recent", methods=["POST"])
def summarize_recent_emails():
    """Summarize recent emails and send WhatsApp alerts"""
    try:
        data = request.json
        hours = data.get("hours", 1)
        count = data.get("count")
        urgent_only = data.get("urgent_only", False)
        
        # Load config
        config = load_config()
        if not config:
            return jsonify({"error": "Not connected to email"}), 401
        
        # Fetch emails
        fetcher = EmailFetcher(config["email"], config["app_password"])
        emails = fetcher.fetch_recent_emails(hours=hours)
        
        if not emails:
            return jsonify({
                "summary": f"No emails found in the last {hours} hour(s).",
                "urgent_count": 0,
                "urgent_emails": [],
                "total_emails": 0
            })
        
        # Apply count limit if specified
        if count and count > 0:
            emails = emails[:count]
        
        # Detect urgent emails
        urgent_emails = detect_urgent_emails(emails)
        
        # If urgent_only is True, filter to only urgent emails
        if urgent_only:
            emails = urgent_emails
        
        # Generate AI summaries for each email
        summarized_emails = []
        email_counter = 1
        for email in emails:
            # Use AI to generate a brief summary of each email
            summary_prompt = f"""Summarize this email in ONE short sentence that captures the main point:

Subject: {email['subject']}
From: {email['from']}
Body: {email['body'][:500]}

Return ONLY the summary sentence, nothing else. Do not include phrases like "Here's a summary" or "This email is about"."""

            try:
                from llm_engine import ask_llm
                ai_summary = ask_llm(summary_prompt, history=[]).strip()
                # Clean up any remaining meta-text
                ai_summary = ai_summary.replace("Here's a summary:", "").replace("This email is about:", "").strip()
            except:
                # Fallback to preview if AI fails
                ai_summary = email['body'][:100] + "..."
            
            summarized_emails.append({
                "number": email_counter,
                "subject": email['subject'],
                "from": email['from'],
                "date": email['date'],
                "summary": ai_summary,
                "is_urgent": email in urgent_emails
            })
            email_counter += 1
        
        # Create a nice formatted summary (like in your image)
        summary_text = "📧 **Summary of Emails:**\n\n"
        for email in summarized_emails:
            summary_text += f"- Email {email['number']}: {email['summary']}\n"
        
        # Prepare urgent emails for response (with email numbers)
        urgent_list = []
        for email in urgent_emails:
            # Find the email number
            email_num = next((e['number'] for e in summarized_emails if e['subject'] == email['subject']), "?")
            urgent_list.append({
                "subject": email['subject'],
                "from": email['from'],
                "number": email_num,
                "urgency_reasons": email.get('urgency_reasons', ['Important'])
            })
        
        # Create urgent alerts text
        urgent_text = ""
        if urgent_list:
            urgent_text = "🔴 **Urgent Alerts:**\n\n"
            for email in urgent_list:
                urgent_text += f"- 🔴 {email['subject']} (Email {email['number']})\n"
        
        # Send WhatsApp alert if urgent emails found
        whatsapp_sent = False
        if urgent_emails and config.get("phone"):
            notifier = WhatsAppNotifier(config["phone"])
            
            # Create alert message
            alert_msg = f"🔴 URGENT: {len(urgent_emails)} urgent email(s) found!\n\n"
            for i, email in enumerate(urgent_emails[:3], 1):
                alert_msg += f"{i}. {email['subject'][:50]}\n"
            
            whatsapp_sent = notifier.send_alert(alert_msg)
        
        return jsonify({
            "success": True,
            "summary": summary_text,
            "urgent_text": urgent_text,
            "urgent_count": len(urgent_emails),
            "urgent_emails": urgent_list,
            "total_emails": len(emails),
            "whatsapp_sent": whatsapp_sent
        })
        
    except Exception as e:
        print(f"Email summary error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/email/generate", methods=["POST"])
def generate_email():
    """Generate email content using AI"""
    try:
        data = request.json
        prompt = data.get("prompt", "")
        system_prompt = data.get("system_prompt", "You are an email composition assistant.")
        is_modification = data.get("is_modification", False)
        
        # Use your existing LLM to generate email
        from llm_engine import ask_llm
        
        if is_modification:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        email_content = ask_llm(full_prompt, history=[])
        
        # Parse subject and body
        lines = email_content.strip().split('\n')
        subject = "No Subject"
        body_start = 0
        
        for i, line in enumerate(lines):
            if line.lower().startswith('subject:'):
                subject = line[8:].strip()
                body_start = i + 1
                break
        
        body = '\n'.join(lines[body_start:]).strip()
        
        return jsonify({
            "success": True,
            "subject": subject,
            "body": body,
            "full_content": email_content
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/email/create-mailto", methods=["POST"])
def create_mailto():
    """Create mailto link for draft"""
    try:
        data = request.json
        to_email = data.get("to", "")
        subject = data.get("subject", "")
        body = data.get("body", "")
        
        mailto_link = create_mailto_link(to_email, subject, body)
        
        return jsonify({
            "success": True,
            "mailto": mailto_link
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route("/email/send", methods=["POST"])
def send_email():
    """Send an email using the connected Gmail account"""
    try:
        data = request.json
        to_email = data.get("to")
        subject = data.get("subject")
        body = data.get("body")
        
        # Load config
        config = load_config()
        if not config:
            return jsonify({"error": "Not connected to email"}), 401
        
        # Use your EmailFetcher class to send email
        # You'll need to add a send_email method to EmailFetcher
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import smtplib
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config["email"]
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config["email"], config["app_password"])
        server.send_message(msg)
        server.quit()
        
        return jsonify({"success": True, "message": "Email sent successfully!"})
        
    except Exception as e:
        print(f"Email send error: {e}")
        return jsonify({"error": str(e)}), 500
    
# ========== DASHBOARD API ENDPOINTS ==========

@app.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get analytics summary for dashboard"""
    try:
        # Load conversations for analytics
        conversations = []
        if os.path.exists('database/conversations.json'):
            with open('database/conversations.json', 'r') as f:
                conversations = json.load(f)
        
        # Load feedback for ratings
        feedbacks = []
        if os.path.exists('database/feedback.json'):
            with open('database/feedback.json', 'r') as f:
                feedbacks = json.load(f)
        
        # Calculate analytics
        total_queries = len(conversations)
        
        # Count by agent
        agent_usage = {}
        for conv in conversations:
            agent = conv.get('agent', 'unknown')
            agent_usage[agent] = agent_usage.get(agent, 0) + 1
        
        # Get today's queries
        today = datetime.now().date()
        today_queries = sum(1 for conv in conversations 
                          if datetime.fromisoformat(conv.get('timestamp', '2000-01-01')).date() == today)
        
        # Get most popular agent
        most_popular = max(agent_usage.items(), key=lambda x: x[1]) if agent_usage else ('None', 0)
        
        # Daily stats for last 7 days
        daily_stats = []
        for i in range(6, -1, -1):
            date = (today - timedelta(days=i)).isoformat()
            count = sum(1 for conv in conversations 
                       if datetime.fromisoformat(conv.get('timestamp', '2000-01-01')).date() == (today - timedelta(days=i)))
            daily_stats.append({
                'date': date,
                'queries': count
            })
        
        # Total agents count
        total_agents = len(set(conv.get('agent', 'unknown') for conv in conversations))
        
        return jsonify({
            'total_queries': total_queries,
            'agent_usage': agent_usage,
            'today_queries': today_queries,
            'most_popular_agent': {
                'name': most_popular[0],
                'count': most_popular[1]
            },
            'total_agents': total_agents or 16,  # Fallback to your 16 agents
            'daily_stats': daily_stats
        })
    
    except Exception as e:
        print(f"Error in analytics: {e}")
        # Return demo data if error
        return jsonify({
            'total_queries': 1250,
            'agent_usage': {
                'Standard Chat': 450,
                'Multi-Bot Search': 320,
                'Web Search Pro': 280,
                'Code Wizard': 200
            },
            'today_queries': 42,
            'most_popular_agent': {
                'name': 'Standard Chat',
                'count': 450
            },
            'total_agents': 16,
            'daily_stats': [
                {'date': (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'), 'queries': 35},
                {'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), 'queries': 42},
                {'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), 'queries': 38},
                {'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), 'queries': 45},
                {'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), 'queries': 51},
                {'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'queries': 47},
                {'date': datetime.now().strftime('%Y-%m-%d'), 'queries': 42}
            ]
        })

@app.route('/history/all', methods=['GET'])
def get_all_history():
    """Get all conversation history"""
    try:
        if os.path.exists('database/conversations.json'):
            with open('database/conversations.json', 'r') as f:
                conversations = json.load(f)
        else:
            conversations = []
        
        # Sort by timestamp descending (newest first)
        conversations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({'conversations': conversations})
    
    except Exception as e:
        print(f"Error loading history: {e}")
        return jsonify({'conversations': [], 'error': str(e)})

@app.route('/database/users.json', methods=['GET'])
def get_users():
    """Get users data"""
    try:
        if os.path.exists('database/users.json'):
            with open('database/users.json', 'r') as f:
                users = json.load(f)
        else:
            # Create sample users if file doesn't exist
            users = [
                {
                    'username': 'admin',
                    'email': 'admin@fusionai.com',
                    'role': 'admin',
                    'total_queries': 150,
                    'last_active': datetime.now().isoformat(),
                    'created_at': (datetime.now() - timedelta(days=30)).isoformat()
                },
                {
                    'username': 'guest_user',
                    'email': 'guest@example.com',
                    'role': 'user',
                    'total_queries': 45,
                    'last_active': datetime.now().isoformat(),
                    'created_at': (datetime.now() - timedelta(days=2)).isoformat()
                }
            ]
            # Save sample users
            os.makedirs('database', exist_ok=True)
            with open('database/users.json', 'w') as f:
                json.dump(users, f, indent=2)
        
        return jsonify(users)
    
    except Exception as e:
        print(f"Error loading users: {e}")
        return jsonify([])
    
@app.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        
        # Load existing feedback
        feedback_file = 'database/feedback.json'
        
        # Create directory if it doesn't exist
        os.makedirs('database', exist_ok=True)
        
        # Load existing feedback or create new list
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                feedbacks = json.load(f)
        else:
            feedbacks = []
        
        # Add new feedback
        feedbacks.append({
            'id': len(feedbacks) + 1,
            'timestamp': data['timestamp'],
            'rating': data['rating'],
            'category': data['category'],
            'message': data['message'],
            'user_id': data['user_id'],
            'status': 'new'
        })
        
        # Save back to file
        with open(feedback_file, 'w') as f:
            json.dump(feedbacks, f, indent=2)
        
        return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/feedback/all', methods=['GET'])
def get_all_feedback():
    try:
        feedback_file = 'database/feedback.json'
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                feedbacks = json.load(f)
        else:
            feedbacks = []
        
        # Sort by timestamp descending (newest first)
        feedbacks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({'feedbacks': feedbacks})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===============================
# Logout Route
# ===============================

@app.route("/logout")
def logout():
    """Clear session and logout user"""
    session.clear()  # Clear all session data
    return redirect(url_for('sign_in'))  # Redirect to sign in page

if __name__ == "__main__":
    app.run(debug=True)