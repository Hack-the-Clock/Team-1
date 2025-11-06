# dashboard_app.py

from flask import Flask, render_template
from flask_socketio import SocketIO
import pika
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

# --- RabbitMQ Listener ---

def swarm_listener():
    """Connects to RabbitMQ and forwards messages to the dashboard."""
    
    connection = None
    while not connection:
        try:
            # Wait 5 seconds between retries
            time.sleep(5)
            print("Dashboard: Trying to connect to RabbitMQ...")
            
            # This is the line that was failing
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            
        except pika.exceptions.AMQPConnectionError:
            print("Dashboard: RabbitMQ not ready. Retrying in 5s...")

    # If we get here, we are connected!
    print("\n[*] Dashboard connected to RabbitMQ and listening.\n")
    
    channel = connection.channel()
    channel.exchange_declare(exchange='swarm_logs', exchange_type='topic')
    
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Bind to all topics (#)
    channel.queue_bind(exchange='swarm_logs', queue=queue_name, routing_key="#")

    def callback(ch, method, properties, body):
        """Called when a message is received."""
        log_message = body.decode()
        print(f" [x] Forwarding log to dashboard: {log_message}")
        # Send the log to the web page
        socketio.emit('new_log', {'data': log_message})

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)

    channel.start_consuming()

# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

if __name__ == '__main__':
    # Start the RabbitMQ listener in a background thread
    print("Starting RabbitMQ listener thread...")
    listener_thread = threading.Thread(target=swarm_listener, daemon=True)
    listener_thread.start()
    
    # Start the web server
    print("Starting Dashboard web server on http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)