# patcher.py

import re

APP_FILE_PATH = "app.py"
FIX_FILE_PATH = "fixed_function.py"

print("Starting Patcher...")

# 1. Read the AI's fixed function
try:
    with open(FIX_FILE_PATH, 'r') as f:
        fixed_function_code = f.read()
    print(f"Loaded AI-generated fix from '{FIX_FILE_PATH}'.")
except FileNotFoundError:
    print(f"ERROR: Could not find fix file: {FIX_FILE_PATH}")
    exit()

# 2. Read the original, vulnerable app.py
try:
    with open(APP_FILE_PATH, 'r') as f:
        vulnerable_app_code = f.read()
    print(f"Loaded vulnerable code from '{APP_FILE_PATH}'.")
except FileNotFoundError:
    print(f"ERROR: Could not find app file: {APP_FILE_PATH}")
    exit()

# 3. Clean the AI's output (remove markdown backticks)
fixed_function_code = fixed_function_code.strip().strip("```python").strip("```")
print("Cleaned AI output (removed markdown).")

# 4. Define the start and end of the function we want to replace
# We use a regex to find the whole function block
function_start = r"@app\.route\('/admin/delete/<int:post_id>', methods=\['GET'\]\)"
function_end = r"# --- !!! END VULNERABLE ROUTE !!! ---"

# 5. Use regex to find and replace the function block
# re.DOTALL (or (?s)) makes the '.' match newlines,
# so it finds the *entire* function block
pattern = re.compile(f"({function_start}.*?{function_end})", re.DOTALL)

if not pattern.search(vulnerable_app_code):
    print("ERROR: Could not find the vulnerable function block in app.py.")
    print("Maybe it's already patched? Or the regex is wrong.")
    exit()

# Perform the replacement
patched_app_code = pattern.sub(fixed_function_code, vulnerable_app_code)

# 6. Save the new, patched code back to app.py
with open(APP_FILE_PATH, "w") as f:
    f.write(patched_app_code)

print("\n" + "="*50)
print(f"*** PATCH APPLIED SUCCESSFULLY ***")
print(f"The file '{APP_FILE_PATH}' has been autonomously patched.")
print("="*50)