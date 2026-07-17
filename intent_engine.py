from llm_engine import llm_classify 

def is_admin_allowed(user_role):
    return user_role == "admin"

def route_user_message(user_text, user_role="user"):
    intent = llm_classify(user_text)

    # Security check
    if intent == "admin" and not is_admin_allowed(user_role):
        return {"intent": "admin", "message": "Unauthorized admin command blocked"}

    return {"intent": intent, "message": "Intent accepted"}