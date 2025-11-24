"""
Core logic for monitoring Gemini API token usage.
Tracks usage by logging requests to a local JSON file.
"""

import os
import json
from datetime import datetime

client = None
init_error = None

# Try to load .env file and import google.genai
try:
    from dotenv import load_dotenv
    # This will search for a .env file in the project root and load it.
    load_dotenv()
except ImportError:
    init_error = "Could not import 'dotenv'. Please run: pip install python-dotenv"

# If dotenv is loaded (or not needed), proceed with google.genai
if not init_error:
    try:
        from google import genai
        # Attempt to initialize the client using the now-loaded environment variable
        if "GEMINI_API_KEY" in os.environ:
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        else:
            init_error = "GEMINI_API_KEY not found. Please create a .env file in the project root with its value."
    except ImportError:
        init_error = "Could not import 'google.genai'. Please run: pip install google-genai"
    except Exception as e:
        init_error = f"Failed to initialize Gemini Client: {e}"

STATS_FILE = "gemini_usage_log.json"

def load_stats():
    """Loads usage statistics from the JSON log file."""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {"total_input_tokens": 0, "total_output_tokens": 0, "total_requests": 0, "history": []}

def save_stats(stats):
    """Saves usage statistics to the JSON log file."""
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def get_stats_summary():
    """Returns a formatted string summary of the current usage stats."""
    if not os.path.exists(STATS_FILE):
        return "No usage data found. Make a request to start logging."
    
    stats = load_stats()
    total_tokens = stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0)
    
    summary = (
        f"Total Requests: {stats.get('total_requests', 0)}\n"
        f"Total Input Tokens: {stats.get('total_input_tokens', 0)}\n"
        f"Total Output Tokens: {stats.get('total_output_tokens', 0)}\n"
        f"------------------\n"
        f"Total Tokens Logged: {total_tokens}\n\n"
        f"Last 10 Requests:\n"
    )
    
    history_lines = []
    for item in reversed(stats.get("history", [])[-10:]):
        ts = item.get('timestamp', 'No date')
        model = item.get('model', 'N/A')
        inp = item.get('input', 0)
        outp = item.get('output', 0)
        history_lines.append(f"- {ts[:19]}: {inp} in, {outp} out ({model})")
        
    return summary + "\n".join(history_lines)

def run_monitored_request(prompt, log_callback, model_name="gemini-pro"):
    """
    Sends a request to the Gemini API, logs the token usage, and uses a callback 
    to send real-time updates to the GUI.
    """
    if not client:
        log_callback(init_error)
        return

    stats = load_stats()
    log_callback(f"--- Sending request to '{model_name}'... ---")
    
    try:
        # 1. (Optional) Estimate token count before sending
        pre_count = client.models.count_tokens(model=model_name, contents=prompt)
        log_callback(f"(Estimated input tokens: {pre_count.total_tokens})")

        # 2. Make the actual API call
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        # 3. Capture and log the usage metadata from the response
        if response.usage_metadata:
            input_tok = response.usage_metadata.prompt_token_count
            output_tok = response.usage_metadata.candidates_token_count
            
            # Update stats dictionary
            stats.setdefault("total_input_tokens", 0)
            stats.setdefault("total_output_tokens", 0)
            stats.setdefault("total_requests", 0)
            stats.setdefault("history", [])

            stats["total_input_tokens"] += input_tok
            stats["total_output_tokens"] += output_tok
            stats["total_requests"] += 1
            
            stats["history"].append({
                "timestamp": datetime.now().isoformat(),
                "model": model_name,
                "input": input_tok,
                "output": output_tok
            })
            
            save_stats(stats)
            
            log_callback(f"Success! Usage: {input_tok} input + {output_tok} output tokens.")
            log_callback(f"Response: {response.text[:200]}...")
        else:
            log_callback("Warning: API call succeeded but no usage metadata was returned.")
            
    except Exception as e:
        log_callback(f"--- ERROR ---\n{e}")
    finally:
        # After the request, provide an updated summary
        log_callback("\n--- Usage Summary ---")
        log_callback(get_stats_summary())

