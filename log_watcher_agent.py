# log_watcher_agent.py

import json
import time
import yaml # You already installed this
from fluent import sender
from fluent import event
from openai import OpenAI # You already installed this

# --- Agent Configuration ---

# !! --- NEW CONFIGURATION FOR LOCAL LLM --- !!
# 1. You've installed Ollama (https://ollama.com)
# 2. You've run: ollama pull gemma:2b
#
# We are now pointing to our LOCAL computer's LLM server.
# No API key or internet needed!
API_KEY = "ollama" # (Ollama doesn't care, but the field needs to be non-empty)
API_BASE_URL = "http://localhost:11434/v1" # This is the Ollama default
MODEL_TO_USE = "gemma:2b" # <-- We're using the model you chose!

RULEBOOK_PATH = 'Rulebook.yaml'

try:
    client = OpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL
    )
    # Test connection
    client.models.list()
    print(f"Successfully connected to local Ollama server. Using model: {MODEL_TO_USE}")
except Exception as e:
    print("="*50)
    print("CRITICAL ERROR: Could not connect to Ollama.")
    print(f"Error: {e}")
    print("\nPlease make sure the Ollama application is running on your computer.")
    print("You can download it from https://ollama.com")
    print("="*50)
    exit()


# --- 1. The "Neuro" (LLM) Parser ---

def ask_llm_to_parse(log_line):
    """
    Uses an LLM to parse a messy log line into structured JSON.
    This is the "Neuro" part.
    """
    print(f"\n[Neuro]: Analyzing log: '{log_line}'")
    
    system_prompt = """
    You are an expert log analysis system. Your job is to parse unstructured logs 
    into a strict JSON format.
    
    The user will provide a log line. You MUST extract the following fields:
    - "log_level": (e.g., "INFO", "CRITICAL", "WARN")
    - "user_name": (The user who performed the action)
    - "user_role": (The role of that user, e.g., "USER", "ADMIN", "GUEST")
    - "action": (A short machine-readable action code. 
                 If you see "ADMIN ACTION... deleted post", 
                 use "admin_delete")
    
    If you cannot find a piece of information, set it to "UNKNOWN".
    Respond ONLY with the single JSON object. Do not add any other text or preamble.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_TO_USE, # This is the model we pulled with Ollama
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": log_line}
            ],
            response_format={"type": "json_object"}
        )
        
        parsed_json_str = response.choices[0].message.content
        parsed_json = json.loads(parsed_json_str)
        
        print(f"[Neuro]: LLM parsed data: {parsed_json}")
        return parsed_json
        
    except Exception as e:
        print(f"[Neuro]: LLM parsing failed. Error: {e}")
        if "Connection refused" in str(e):
            print("[Neuro]: --- HINT ---")
            print("[Neuro]: Connection refused. Is the Ollama server running?")
            print("[Neuro]: Try running 'ollama serve' in a new terminal.")
            print("[Neuro]: --- HINT ---")
        return None

# --- 2. The "Symbolic" (Rules) Engine ---

def check_rules(parsed_log, rules):
    """
    Checks the structured data from the LLM against our "Rulebook."
    This is the "Symbolic" part.
    """
    for rule in rules['Rules']:
        print(f"\n[Symbolic]: Checking rule: '{rule['name']}'...")
        conditions = rule['conditions']
        
        # This is a simple logic engine.
        # We check if the parsed log matches all conditions in the rule.
        try:
            # Check condition 1: log_level == 'CRITICAL'
            if not parsed_log['log_level'] == 'CRITICAL':
                continue # This log isn't CRITICAL, skip.
                
            # Check condition 2: action == 'admin_delete'
            if not parsed_log['action'] == 'admin_delete':
                continue # Not the action we're looking for, skip.
            
            # Check condition 3: user_role != 'ADMIN'
            if not parsed_log['user_role'] != 'ADMIN':
                print("[Symbolic]: ...Rule not broken. (User was an Admin)")
                continue # User was an admin, so no breach.
            
            # If we get here, all conditions matched!
            print("=" * 40)
            print(f"[Symbolic]: *** LOGIC BREACH DETECTED ***")
            print(f"[Symbolic]: Rule '{rule['name']}' was violated.")
            print(f"[Symbolic]: REPORT: User '{parsed_log['user_name']}' (Role: {parsed_log['user_role']}) performed '{parsed_log['action']}'")
            print("=" * 40)
            return True # Breach detected
            
        except KeyError as e:
            print(f"[Symbolic]: Could not check rule. LLM did not provide key: {e}")
        
    print("[Symbolic]: ...No rules broken.")
    return False # No breach detected

# --- 3. The Main Listener Loop ---

def main():
    print("Starting Log-Watcher Agent (v1)...")
    
    # Load the "brain"
    with open(RULEBOOK_PATH, 'r') as f:
        rules = yaml.safe_load(f)
    print(f"Loaded {len(rules['Rules'])} rules from {RULEBOOK_PATH}.")

    # --- Test Harness ---
    print("\nAgent 2 is testing its local LLM and Rules engine...")
    
    # We'll use the *exact* log our Monkey generated.
    test_log = '[CRITICAL] ADMIN ACTION: User monkey_user (role: USER) deleted post 1.'
    
    # 1. Test the "Neuro" part
    parsed_data = ask_llm_to_parse(test_log)
    
    # 2. Test the "Symbolic" part
    if parsed_data:
        check_rules(parsed_data, rules)
    
    # --- Test with a non-violating log ---
    print("\n--- Testing a non-violating log ---")
    test_log_safe = '[CRITICAL] ADMIN ACTION: User admin_user (role: ADMIN) deleted post 2.'
    
    # 1. Test "Neuro"
    parsed_data_safe = ask_llm_to_parse(test_log_safe)
    
    # 2. Test "Symbolic"
    if parsed_data_safe:
        check_rules(parsed_data_safe, rules)


if __name__ == "__main__":
    main()