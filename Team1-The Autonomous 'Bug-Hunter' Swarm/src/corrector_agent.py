# corrector_agent.py

import json
from openai import OpenAI
import os

# --- Agent Configuration ---
API_KEY = "ollama"
API_BASE_URL = "http://localhost:11434/v1"
MODEL_TO_USE = "gemma:2b"
CODE_FILE_PATH = "app.py"

try:
    client = OpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL
    )
    client.models.list()
    print(f"Successfully connected to local Ollama server. Using model: {MODEL_TO_USE}")
except Exception as e:
    print("="*50)
    print("CRITICAL ERROR: Could not connect to Ollama.")
    print(f"Error: {e}")
    print("\nPlease make sure the Ollama application is running on your computer.")
    print("="*50)
    exit()

# --- 1. The "Surgeon" (LLM Coder) ---

def ask_llm_to_fix_code(breach_report, code_content):
    """
    Uses an LLM to read a bug report and source code,
    and then generate the *full, fixed function*.
    """
    print("\n[Corrector]: Analyzing code to find fix (Attempt 4: Function Replace)...")
    
    # --- !! NEW PROMPT: Ask for the function, not a diff !! ---
    system_prompt = f"""
    You are an expert Python developer. You will be given a bug report and a
    full Python code file.
    
    The bug is in the function 'def delete_post(post_id):'.
    This function is missing an admin role check.
    
    Your job is to rewrite the *entire* 'def delete_post(post_id):' function
    , from 'def' to its last line, with the security fix included.
    The fix is to add a check for 'current_user.role != "ADMIN"' and
    abort(403) if the user is not an admin.
    
    Respond ONLY with the complete, corrected Python function.
    Do not add any other text, explanations, or markdown backticks.
    Start your response with '@app.route'.
    """
    
    user_prompt = f"""
    --- LOGIC BREACH REPORT ---
    {breach_report}
    
    --- VULNERABLE CODE: {CODE_FILE_PATH} ---
    {code_content}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_TO_USE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        
        fixed_function = response.choices[0].message.content
        
        print("\n" + "="*50)
        print(f"[Corrector]: *** AUTONOMOUSLY FIXED FUNCTION ***")
        print(fixed_function)
        print("="*50)
        return fixed_function
        
    except Exception as e:
        print(f"[Corrector]: LLM patch generation failed. Error: {e}")
        return None

# --- 2. The Main Test Harness ---

def main():
    print("Starting Corrector Agent (v1)...")
    
    breach_report = """
    Rule 'Admin_Access_Violation' was violated.
    REPORT: User 'monkey_user' (Role: 'USER') performed 'admin_delete'
    on the route '/admin/delete/<int:post_id>'
    """
    print(f"Test breach report loaded.")
    
    try:
        with open(CODE_FILE_PATH, 'r') as f:
            code_content = f.read()
        print(f"Successfully loaded code from '{CODE_FILE_PATH}'.")
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Code file not found at '{CODE_FILE_PATH}'.")
        exit()
    
    # Generate the fix
    fixed_function_code = ask_llm_to_fix_code(breach_report, code_content)
    
    if fixed_function_code:
        # Save the fix to a new file
        # This is what our final agent will do
        with open("fixed_function.py", "w") as f:
            f.write(fixed_function_code)
        print(f"\n[Corrector]: Saved fixed function to 'fixed_function.py'")


if __name__ == "__main__":
    main()