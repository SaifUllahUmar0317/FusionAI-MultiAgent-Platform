from concurrent.futures import ThreadPoolExecutor, as_completed
from llm_engine import ask_llm, ask_llm_model2, ask_llm_model3
import time

def judge_best_answer(user_prompt, responses):
    """
    Uses primary LLM as judge to select best response.
    """
    try:
        # If only one response, return it directly
        if len(responses) == 1:
            return list(responses.values())[0]
            
        judge_prompt = f"""
You are an expert evaluator. Select the best answer.

User Question:
{user_prompt}

{chr(10).join([f"Answer {k}: {v[:200]}..." for k, v in responses.items()])}

Reply ONLY with the letter of the best answer.
"""
        verdict = ask_llm(judge_prompt, []).strip().upper()
        
        # Extract just the letter
        for letter in responses.keys():
            if letter in verdict:
                return responses[letter]
    except Exception as e:
        print(f"Judge error: {e}")
    
    # Fallback to first response
    return list(responses.values())[0]


def run_multi_bot(prompt, history=None):
    """
    Runs multiple LLMs in parallel and returns the best answer.
    Optimized for speed.
    """
    print(f"🚀 Running multi-bot for: {prompt[:50]}...")
    start_time = time.time()
    
    responses = {}
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks with shorter timeout
        future_map = {
            executor.submit(ask_llm, prompt, history): "A",
            executor.submit(ask_llm_model2, prompt, history): "B",
            executor.submit(ask_llm_model3, prompt, history): "C"
        }
        
        # Collect results with timeout
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                # Wait max 15 seconds per model
                result = future.result(timeout=15)
                if result and not result.startswith('['):
                    responses[key] = result
                    print(f"✅ Model {key} responded in {time.time()-start_time:.1f}s")
            except Exception as e:
                print(f"❌ Model {key} failed: {e}")
    
    elapsed = time.time() - start_time
    print(f"⏱️ Multi-bot completed in {elapsed:.1f} seconds with {len(responses)} responses")
    
    # If no responses, use a fallback
    if not responses:
        return "I'm processing your request. Please try again in a moment."
    
    # If we have responses, judge them
    if len(responses) > 1:
        best = judge_best_answer(prompt, responses)
    else:
        best = list(responses.values())[0]
    
    return best