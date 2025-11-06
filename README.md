🚀 Autonomous Bug-Hunter Swarm

This is a "Digital Immune System"—an autonomous swarm of AI agents that find, diagnose, and write the code to fix security vulnerabilities in a live web application, all in real-time.

This project demonstrates how AI agents can go beyond simple code generation to actively heal and maintain a codebase. The entire system runs 100% locally using Docker, Ollama, and a message queue.

(This README assumes you have a GIF of the dashboard in action. If not, you can remove this line.)

🛠️ Tech Stack

Application: Python, Flask, SQLAlchemy

AI: Ollama with gemma:2b (local LLM), openai Python library

Infrastructure: Docker, Docker Compose

Messaging / "Nervous System": RabbitMQ

Logging: Fluentd

Front-End: Flask-Socket.IO, HTML/CSS/JavaScript

🏗️ Architecture: How It Works

The system is built on a message-driven architecture. A central message queue, RabbitMQ, acts as the "nervous system" that allows the four specialized agents to communicate and trigger each other in a chain.

🐒 The Monkey (Agent 1): The Attacker

Job: To find vulnerabilities.

Action: It logs in as a normal USER and attempts to run a known admin-only function (deleting a post). If the attack succeeds, it publishes a VULNERABILITY_FOUND message.

🕵️ The Log-Watcher (Agent 2): The "Brain"

Job: To diagnose why the bug happened.

Action: This is a neurosymbolic agent.

Neuro (LLM): It uses gemma:2b to read the server's log ([CRITICAL]... User 'monkey_user' (role: USER)...) and parse that messy text into structured JSON.

Symbolic (Rules): It checks that JSON against the Rulebook.yaml. The rule says: "If action is admin_delete and user_role is NOT ADMIN, it's a logic breach!"

It then publishes a detailed LOGIC_BREACH_DETECTED report.

🩺 The Corrector (Agent 3): The "Surgeon"

Job: To write the code fix.

Action: It listens for the breach report. It reads the application's actual source code (app.py) and feeds it to the gemma:2b LLM with a specific prompt: "Here is a bug report and here is the code. Please rewrite the vulnerable function to fix it."

It then publishes the AI-generated, fixed Python code as a PATCH_GENERATED message.

🛠️ The Patcher (Agent 4): The "Robot"

Job: To apply the fix.

Action: It listens for the patch. It intelligently extracts the clean code (ignoring the AI's "chatty" explanations) and uses Regex to find and replace the vulnerable function in app.py on the live server.

It then publishes the final BUG_FIXED message.

🚀 How to Run the Demo

Prerequisites

Docker Desktop: Must be installed and running.

Ollama: Must be installed and running.

Python 3.10+

Step 1: Get the Local LLM

In your terminal, pull the gemma:2b model:

ollama pull gemma:2b


Step 2: Install Host Python Libraries

These are required for the swarm_controller.py to run on your machine.

pip install requests pika openai pyyaml


Step 3: Reset the Project (Do this for every demo)

The swarm is designed to fix the bug. To run the demo, you must first make the app vulnerable again.

1. Reset the Code:
Open app.py. Find the delete_post function and replace it with the original vulnerable code:

# --- !!! THE VULNERABLE ROUTE !!! ---
@app.route('/admin/delete/<int:post_id>', methods=['GET'])
@login_required # <-- PROBLEM: This checks for LOGIN, but not for ADMIN role!
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # CRITICAL LOGIC FLAW IS HERE
    # A regular 'USER' can access this route and delete anyone's post.
    # This is the "logic breach" our Log-Watcher will be built to detect.
    
    db.session.delete(post)
    db.session.commit()
    
    # This log line is the "smoking gun" our Log-Watcher will find
    app.logger.critical(f"ADMIN ACTION: User {current_user.username} (role: {current_user.role}) deleted post {post_id}.")
    return f"Post {post_id} deleted by {current_user.username}."
# --- !!! END VULNERABLE ROUTE !!! ---


Save the app.py file.

2. Reset the Database:
Delete the database file:

# On PowerShell
Remove-Item .\instance\app.db -ErrorAction SilentlyContinue

# On macOS/Linux
rm -f ./instance/app.db


Step 4: Launch the System (The 3-Step-Launch)

You need two terminals for this.

In Terminal 1: Start the Servers

docker-compose up


Wait for all services to be running (especially victim-app and dashboard).

In Terminal 2: Initialize the Database
This command creates the user and post tables in the new, empty database.

docker exec victim-app flask init-db


You should see: Initialized the database.

In Your Browser: Open the Dashboard
Go to: http://localhost:5001

In Terminal 2: Run the Swarm!
Now, run the main controller script:

python swarm_controller.py


Step 5: Watch the Dashboard

You will see the entire "find-and-fix" loop execute in real-time on your dashboard.

Step 6: Verify the Fix

After the first run is complete (the dashboard says BUG FIXED), run the controller a second time in Terminal 2:

python swarm_controller.py


This time, the dashboard will show the "proof" that the patch worked:
[MONKEY] Attack failed. Bug is already fixed. (Server returned 403 Forbidden)

