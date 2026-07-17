from llm_engine import ask_llm, fetch_live_data, llm_classify
from multi_bot import run_multi_bot
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def fusionai(user_text, history, user_role="user", multi=False):
    """
    Simplified fusionai using friend's approach
    - Supports conversation history
    - Multi-agent mode support
    - Intent classification via llm_classify
    """
    try:
        logger.debug(f"fusionai called with text: {user_text[:50]}..., multi: {multi}")
        
        # 1. Detect Intent
        try:
            intent = llm_classify(user_text)
            logger.debug(f"Classified intent: {intent}")
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            intent = "chat"  # Default to chat on error
        
        # 2. Execution Logic
        if multi:
            logger.debug("Running in multi mode")
            if intent == "latest_update":
                return fetch_live_data(user_text)
            else:
                # For all other intents in multi mode
                return run_multi_bot(user_text, history)
        else:
            logger.debug("Running in single mode")
            if intent == "latest_update":
                return fetch_live_data(user_text)
            elif intent == "chat":
                return ask_llm(user_text, history)
            elif intent == "support":
                return ask_llm(f"Campus support needed: {user_text}", history)
            elif intent == "report":
                return ask_llm(f"Generate a report: {user_text}", history)
            else:
                # Default to chat for any other intent
                return ask_llm(user_text, history)
    
    except Exception as e:
        logger.error(f"Error in fusionai: {e}")
        traceback.print_exc()
        return f"I encountered an error processing your request: {str(e)}"