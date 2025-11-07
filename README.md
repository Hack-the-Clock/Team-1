# 🚀 Autonomous Bug-Hunter Swarm

_“Digital Immune System”—an autonomous swarm of AI agents that find, diagnose, and fix security vulnerabilities in a live web application, in real-time._

This project demonstrates how AI agents can do more than generate code; they actively heal and maintain a codebase. Everything runs 100% locally using Docker, Ollama, and a message queue.


---

## 🛠️ Tech Stack

- **Application:** Python, Flask, SQLAlchemy
- **AI:** Ollama with gemma:2b (local LLM), openai Python library
- **Infrastructure:** Docker, Docker Compose
- **Messaging / "Nervous System":** RabbitMQ
- **Logging:** Fluentd
- **Front-End:** Flask-Socket.IO, HTML/CSS/JavaScript

---

## 🏗️ Architecture: How It Works

The system uses a message-driven architecture. RabbitMQ acts as the “nervous system” for four specialized agents that communicate and trigger each other in sequence.

### 🐒 The Monkey (Agent 1): The Attacker

- **Job:** Find vulnerabilities
- **Action:** Logs in as a normal USER, tries to run an admin-only function (deleting a post). If successful, publishes a `VULNERABILITY_FOUND` message.

### 🕵️ The Log-Watcher (Agent 2): The "Brain"

- **Job:** Diagnose why the bug happened
- **Action:** Neurosymbolic agent.
  - **Neuro (LLM):** Uses gemma:2b to parse server logs into structured JSON.
  - **Symbolic (Rules):** Checks JSON against `Rulebook.yaml`.  
    Rule: _If action is `admin_delete` and `user_role` is NOT ADMIN, flag logic breach!_
  - Publishes detailed `LOGIC_BREACH_DETECTED` report.

### 🩺 The Corrector (Agent 3): The "Surgeon"

- **Job:** Write the code fix
- **Action:** Listens for breach reports, reads source code (`app.py`), sends it to gemma:2b with a prompt:  
  _“Here is a bug report and here is the code. Please rewrite the vulnerable function to fix it.”_
- Publishes `PATCH_GENERATED` message with the fixed Python code.

### 🛠️ The Patcher (Agent 4): The "Robot"

- **Job:** Apply the fix
- **Action:** Listens for code patch, intelligently extracts clean code, uses Regex to replace the vulnerable function in `app.py` on the live server.
- Publishes final `BUG_FIXED` message.

---

## 🚀 How to Run the Demo

### Prerequisites

- **Docker Desktop:** Installed and running
- **Ollama:** Installed and running
- **Python 3.10+**

### Step 1: Get the Local LLM

```sh
ollama pull gemma:2b
```

### Step 2: Install Host Python Libraries

For the `swarm_controller.py` to run locally:

```sh
pip install requests pika openai pyyaml
```

### Step 3: Reset the Project _(Do this for every demo)_

#### 1. Reset the Code

Open `app.py`. Replace the `delete_post` function with the original vulnerable code:

```python
# --- !!! THE VULNERABLE ROUTE !!! ---
@app.route('/admin/delete/<int:post_id>', methods=['GET'])
@login_required  # <-- PROBLEM: Checks for LOGIN, not ADMIN role!
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # CRITICAL LOGIC FLAW HERE
    # A regular 'USER' can access this route and delete anyone's post.
    # This is the "logic breach" our Log-Watcher will detect.
    
    db.session.delete(post)
    db.session.commit()
    
    # This log line is the "smoking gun" our Log-Watcher finds
    app.logger.critical(f"ADMIN ACTION: User {current_user.username} (role: {current_user.role}) deleted post {post_id}.")
    return f"Post {post_id} deleted by {current_user.username}."
# --- !!! END VULNERABLE ROUTE !!! ---
```

_Save the file._

#### 2. Reset the Database

Delete the database file:

**On PowerShell:**
```sh
Remove-Item .\instance\app.db -ErrorAction SilentlyContinue
```

**On macOS/Linux:**
```sh
rm -f ./instance/app.db
```

---

### Step 4: Launch the System (“3-Step-Launch”)

You'll need two terminals:

#### Terminal 1: Start the Servers

```sh
docker-compose up
```
Wait for all services to be running (especially `victim-app` and `dashboard`).

#### Terminal 2: Initialize the Database

This creates the user and post tables in the new database:

```sh
docker exec victim-app flask init-db
```

You should see: _Initialized the database._

#### In Your Browser: Open the Dashboard

Go to: [http://localhost:5001](http://localhost:5001)

---

#### Terminal 2: Run the Swarm

```sh
python swarm_controller.py
```

---

### Step 5: Watch the Dashboard

You'll see the full “find-and-fix” loop execute in real-time.

---

### Step 6: Verify the Fix

After the first run (dashboard says "BUG FIXED"), re-run the controller in Terminal 2:

```sh
python swarm_controller.py
```

This time, dashboard should prove the patch worked:
> [MONKEY] Attack failed. Bug is already fixed. (Server returned 403 Forbidden)

---

## 📂 Project Structure

```
/
├── app.py                  # Vulnerable Flask victim application
├── swarm_controller.py     # Main script (contains all 4 agents)
├── dashboard_app.py        # Flask/Socket.IO server for dashboard
├── patcher.py              # (Standalone test script)
├── corrector_agent.py      # (Standalone test script)
├── log_watcher_agent.py    # (Standalone test script)
├── monkey_agent.py         # (Standalone test script)
│
├── docker-compose.yml      # Orchestrates all services
├── Dockerfile              # Defines 'victim-app' container
├── Dockerfile.dashboard    # Defines 'dashboard' container
│
├── Rulebook.yaml           # "Symbolic brain" for Log-Watcher
├── fluent.conf             # Fluentd logger config
├── requirements.txt        # Python libraries for containers
│
├── templates/
│   └── index.html          # Dashboard HTML/CSS/JS
│
└── instance/
    └── app.db              # Volatile application database
```