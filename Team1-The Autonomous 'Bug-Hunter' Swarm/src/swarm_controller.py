# swarm_controller.py
#
# This single file contains all our agents,
# now connected by a message queue.

import pika
import time
import requests
import yaml
from openai import OpenAI
import re
import subprocess
import json
import sys

# --- Agent Configuration ---
RABBITMQ_HOST = 'localhost' # We're running this from our host
BASE_URL = "http://localhost:5000"

# Ollama (Local LLM)
API_KEY = "ollama"
API_BASE_URL = "http://localhost:11434/v1"
MODEL_TO_USE = "gemma:2b"

# --- Helper: Swarm Logger ---
# This function is how our agents will talk
def log_to_swarm(agent_name, message, routing_key="log"):
    """Publishes a log message to the RabbitMQ swarm exchange."""
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange='swarm_logs', exchange_type='topic')
        
        full_message = f"[{agent_name}] {message}"
        
        channel.basic_publish(
            exchange='swarm_logs',
            routing_key=routing_key,
            body=full_message
        )
        print(full_message) # Also print to console
        connection.close()
    except pika.exceptions.AMQPConnectionError:
        print(f"[{agent_name}] ERROR: Could not connect to RabbitMQ at {RABBITMQ_HOST}")

# --- LLM Client ---
try:
    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    client.models.list()
    log_to_swarm("SYSTEM", f"Connected to local LLM ({MODEL_TO_USE}).", "system.init")
except Exception as e:
    log_to_swarm("SYSTEM", f"CRITICAL ERROR: Could not connect to Ollama. {e}", "system.error")
    sys.exit()

# --- Agent 1: The Monkey (v2 - More Robust) ---
def run_monkey_agent():
    log_to_swarm("MONKEY", "Starting (v2)... looking for vulnerabilities.", "monkey.start")
    session = requests.Session()
    
    try:
        # --- Step 1: Register ---
        log_to_swarm("MONKEY", "Registering user 'monkey_user'...", "monkey.action")
        r = session.get(
            f"{BASE_URL}/register",
            params={'username': 'monkey_user', 'password': 'monkeypass'}
        )
        # Register either returns 200 (if new) or 400 (if exists). Both are fine.
        if r.status_code not in [200, 400]:
            raise Exception(f"Register step failed! Status: {r.status_code}, Text: {r.text}")
        
        # --- Step 2: Login ---
        log_to_swarm("MONKEY", "Logging in as 'monkey_user'...", "monkey.action")
        r = session.get(
            f"{BASE_URL}/login",
            params={'username': 'monkey_user', 'password': 'monkeypass'}
        )
        # --- FIX 1 ---
        if r.status_code != 200 or "<h1>Blog Posts</h1>" not in r.text:
             raise Exception(f"Login step failed! Status: {r.status_code}, Text: {r.text}")
        log_to_swarm("MONKEY", "Login successful. Session is authenticated.", "monkey.info")

        # --- Step 3: Create Post ---
        # We need a post to exist *before* we can delete it.
        post_id_to_attack = 1
        log_to_swarm("MONKEY", f"Creating post {post_id_to_attack}...", "monkey.action")
        r = session.get(
            f"{BASE_URL}/create_post",
            params={'title': 'Monkey Post', 'content': '...'}
        )
        # --- FIX 2 ---
        if r.status_code != 200 or "<h1>Blog Posts</h1>" not in r.text:
            raise Exception(f"Create Post step failed! Status: {r.status_code}, Text: {r.text}")
        log_to_swarm("MONKEY", f"Post {post_id_to_attack} created.", "monkey.info")

        # --- Step 4: The Attack ---
        log_to_swarm("MONKEY", f"Running exploit: Deleting Post {post_id_to_attack} AS A NORMAL USER...", "monkey.attack")
        r = session.get(f"{BASE_URL}/admin/delete/{post_id_to_attack}")
        
        # --- THIS IS THE NEW, SMARTER CHECK ---
        if r.status_code == 200 and f"deleted by {session.cookies.get('username', 'monkey_user')}" in r.text:
            # SUCCESS! The bug is real.
            log_to_swarm("MONKEY", f"*** VULNERABILITY CONFIRMED *** Server said: '{r.text}'", "monkey.success")
            # This is the message that triggers the next agent
            log_to_swarm("WATCHER", "Monkey found a bug! Analyzing...", "watcher.start")
            run_log_watcher_agent() # Start the next agent
        elif r.status_code == 403:
            # The bug is already fixed
            log_to_swarm("MONKEY", f"Attack failed. Bug is already fixed. (Server returned 403 Forbidden)", "monkey.fail")
        else:
            # Any other response is an unexpected failure
            log_to_swarm("MONKEY", f"Attack failed. Unexpected response. (Code: {r.status_code}, Text: {r.text})", "monkey.error")

    except Exception as e:
        log_to_swarm("MONKEY", f"Agent failed: {e}", "monkey.error")
        return

# --- Agent 2: The Log-Watcher ---
def run_log_watcher_agent():
    # 1. Neuro (Parse Log)
    test_log = '[CRITICAL] ADMIN ACTION: User monkey_user (role: USER) deleted post 1.'
    log_to_swarm("WATCHER", f"Analyzing log: '{test_log}'", "watcher.analyze")
    
    system_prompt = "You are a log parser. Extract log_level, user_name, user_role, and action ('admin_delete') into JSON. Respond ONLY with JSON."
    try:
        response = client.chat.completions.create(
            model=MODEL_TO_USE,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": test_log}],
            response_format={"type": "json_object"}
        )
        parsed_json = json.loads(response.choices[0].message.content)
        log_to_swarm("WATCHER", f"LLM parsed log: {parsed_json}", "watcher.result")
    except Exception as e:
        log_to_swarm("WATCHER", f"LLM parsing failed. Aborting. {e}", "watcher.error")
        return
            
    # 2. Symbolic (Check Rules)
    if (parsed_json['log_level'] == 'CRITICAL' and
        parsed_json['action'] == 'admin_delete' and
        parsed_json['user_role'] != 'ADMIN'):
        
        report = f"User '{parsed_json['user_name']}' (Role: {parsed_json['user_role']}) performed '{parsed_json['action']}'"
        log_to_swarm("WATCHER", f"*** LOGIC BREACH DETECTED *** {report}", "watcher.success")
        
        # Trigger the next agent
        log_to_swarm("CORRECTOR", "Logic breach detected! Generating patch...", "corrector.start")
        run_corrector_agent(report)
    else:
        log_to_swarm("WATCHER", "Log was not a violation. Standing down.", "watcher.fail")

# --- Agent 3: The Corrector ---
def run_corrector_agent(breach_report):
    # 1. Load vulnerable code
    with open("app.py", 'r') as f:
        code_content = f.read()
            
    # 2. Ask LLM to generate the *fixed function*
    system_prompt = "Rewrite the 'def delete_post(post_id):' function to fix a missing admin check. Add a check for 'current_user.role != \"ADMIN\"' and abort(403). Respond ONLY with the complete, corrected Python function, starting with '@app.route'."
    user_prompt = f"--- BUG REPORT ---\n{breach_report}\n\n--- CODE ---\n{code_content}"
    
    log_to_swarm("CORRECTOR", "Asking LLM to write the patch...", "corrector.analyze")
    try:
        response = client.chat.completions.create(
            model=MODEL_TO_USE,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
        fixed_function_code = response.choices[0].message.content
        log_to_swarm("CORRECTOR", "Patch generated by AI.", "corrector.success")
        
        # Trigger the next agent
        log_to_swarm("PATCHER", "New patch received. Applying to app.py...", "patcher.start")
        run_patcher_agent(fixed_function_code)
    except Exception as e:
        log_to_swarm("CORRECTOR", f"LLM patch generation failed. Aborting. {e}", "corrector.error")

# --- Agent 4: The Patcher (v2 - More Robust) ---
# --- Agent 4: The Patcher (v3 - Smart Extractor) ---
def run_patcher_agent(fixed_function_code):
    app_file_path = "app.py"
    try:
        # 1. Read vulnerable code
        with open(app_file_path, 'r') as f:
            vulnerable_app_code = f.read()

        # 2. --- NEW, SMARTEST CLEANING LOGIC ---
        log_to_swarm("PATCHER", "Cleaning AI patch output (v3)...", "patcher.clean")
        
        clean_code = ""
        
        # Try to find a markdown code block first
        code_block_match = re.search(r"```(python)?(.*?)```", fixed_function_code, re.DOTALL)
        
        if code_block_match:
            # Found a markdown block, extract the code
            clean_code = code_block_match.group(2)
            log_to_swarm("PATCHER", "Extracted code from markdown block.", "patcher.clean_ok")
        else:
            # No markdown block, fall back to the '@app.route' logic
            log_to_swarm("PATCHER", "No markdown. Falling back to '@app.route' find.", "patcher.clean_fallback")
            code_start_index = fixed_function_code.find("@app.route")
            if code_start_index != -1:
                clean_code = fixed_function_code[code_start_index:]
            else:
                log_to_swarm("PATCHER", f"ERROR: AI patch invalid. No code found.", "patcher.error")
                return

        # Final strip to remove any extra whitespace
        clean_code = clean_code.strip()
        
        if not clean_code:
            log_to_swarm("PATCHER", f"ERROR: AI patch was empty after cleaning.", "patcher.error")
            return
        # --- END OF NEW LOGIC ---

        # 3. Define the regex for the function to replace
        function_start = r"@app\.route\('/admin/delete/<int:post_id>', methods=\['GET'\]\)"
        function_end = r"# --- !!! END VULNERABLE ROUTE !!! ---"
        pattern = re.compile(f"({function_start}.*?{function_end})", re.DOTALL)
        
        # 4. Apply the patch
        patched_app_code = pattern.sub(clean_code, vulnerable_app_code)
        
        # 5. Save the patched code
        with open(app_file_path, "w") as f:
            f.write(patched_app_code)
        
        log_to_swarm("PATCHER", "*** BUG FIXED *** 'app.py' has been autonomously patched.", "patcher.success")
        log_to_swarm("SYSTEM", "Swarm is standing by. Run monkey again to confirm fix.", "system.done")

    except Exception as e:
        log_to_swarm("PATCHER", f"Patching failed! {e}", "patcher.error")
# --- Main Controller ---
if __name__ == "__main__":
    log_to_swarm("SYSTEM", "Autonomous Bug-Hunter Swarm is online.", "system.start")
    log_to_swarm("SYSTEM", "Triggering Monkey Agent in 3 seconds...", "system.init")
    time.sleep(3)
    run_monkey_agent()