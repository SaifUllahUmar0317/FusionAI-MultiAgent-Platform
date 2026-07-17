import os

from groq import Groq
from tavily import TavilyClient

# ----------------------------
# API Clients
# ----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# Use your SYSTEM_PROMPT (it's more comprehensive)
SYSTEM_PROMPT = "You are FusionAI, a helpful AI assistant. You can help users with various tasks including web browsing, summarizing content, analyzing webpages, extracting information, answering questions, and providing insights. Be helpful, concise, and informative."

def ask_llm(prompt, history=None):
    """
    Modified to support conversation memory.
    """
    try:
        print(f"📞 ask_llm called with prompt: {prompt[:50]}...")
        
        # Initialize messages with the system instruction
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history if it exists and is valid
        if history and isinstance(history, list):
            # Only add the last 5 messages to avoid context overflow
            for msg in history[-5:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
        
        # Add the current user prompt
        messages.append({"role": "user", "content": prompt})
        
        if client is None:
            return "Groq API key is not configured. Set the GROQ_API_KEY environment variable and try again."

        print(f"📤 Sending {len(messages)} messages to Groq...")
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.2,
            max_tokens=1000
        )
        
        response = completion.choices[0].message.content.strip()
        print(f"📥 Received response: {response[:50]}...")
        
        return response
        
    except Exception as e:
        print(f"❌ Error in ask_llm: {e}")
        import traceback
        traceback.print_exc()
        return f"I encountered an error: {str(e)}"

# ===============================
# ADD THESE MULTI-MODEL FUNCTIONS (from his version)
# ===============================
def ask_llm_model2(prompt, history=None):
    """Second model for multi-agent mode"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if history and isinstance(history, list):
            messages.extend(history[-5:])
        
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error in ask_llm_model2: {e}")
        return f"[Model2 error: {str(e)}]"

def ask_llm_model3(prompt, history=None):
    """Third model for multi-agent mode"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if history and isinstance(history, list):
            messages.extend(history[-5:])
        
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=messages,
            temperature=0.4,
            max_tokens=1000
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error in ask_llm_model3: {e}")
        return f"[Model3 error: {str(e)}]"

# ===============================
# Live Web Search Logic
# ===============================
def fetch_live_data(query):
    try:
        if tavily is None:
            return "Tavily API key is not configured. Set the TAVILY_API_KEY environment variable and try again."

        # 1. Search the web
        search_result = tavily.search(query, search_depth="basic", max_results=3)
        
        # 2. Extract snippets into context
        context = ""
        for res in search_result['results']:
            context += f"\n- {res['content']} (Source: {res['url']})"
        
        # 3. Use LLM to summarize findings
        summary_prompt = f"""
        You are a real-time researcher. Using the search results below, answer the user query accurately.
        User Query: {query}
        Search Results: {context}
        
        Instruction: Be concise and mention that this is the latest information.
        """
        return ask_llm(summary_prompt)
    except Exception as e:
        print(f"❌ Error in fetch_live_data: {e}")
        return f"Sorry, I couldn't fetch live data: {str(e)}"

# ===============================
# LLM Intent Classifier
# ===============================
def llm_classify(text):
    try:
        prompt = f"""
You are an intent classifier.
Classify this message into exactly ONE of: latest_update, chat, support, task, report, admin.

Rules:
- latest news, todays temperature, stock prices, or real-time web info → latest_update
- (like submitting assignment, sending email, updating profile) → task
- Otherwise (e.g: hello, hi, casual talk) → chat

Return ONLY the category name.

Message: {text}
Answer:
"""
        reply = ask_llm(prompt).lower().strip()

        for category in ["latest_update", "chat", "support", "task", "report", "admin"]:
            if category in reply:
                return category

        return "chat"
    except Exception as e:
        print(f"❌ Error in llm_classify: {e}")
        return "chat"  # Default to chat on error
    
# Add to llm_engine.py if not already there

def summarize_emails(email_texts):
    """Summarize multiple emails"""
    prompt = f"""Summarize these emails and extract key information:

{email_texts}

Provide:
1. Overall summary
2. Important deadlines/dates
3. Action items
4. Urgent matters

Keep it concise but comprehensive."""
    
    return ask_llm(prompt, history=[])