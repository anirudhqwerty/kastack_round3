import websocket
import time
import random

# Load the sample logs into memory
try:
    with open("sample_data/sample.log", "r") as f:
        # We strip the from the first line
        lines = [line.strip() for line in f.readlines()]
        lines[0] = lines[0].split("] ", 1)[-1] 
except FileNotFoundError:
    print("Error: sample_data/sample.log not found.")
    print("Please run this script from the project root directory.")
    exit(1)

if not lines:
    print("Error: sample.log is empty.")
    exit(1)

# The WebSocket URL your FastAPI server is running
ws_url = "ws://localhost:8000/ws/logs"

print(f"Connecting to {ws_url}...")
print(f"Will send one random log every 3 seconds. Press Ctrl+C to stop.")

while True:
    try:
        # Create a new connection for each message
        ws = websocket.create_connection(ws_url)
        
        # Pick a random log line from your sample file
        log_line = random.choice(lines)
        
        # Send the log line
        ws.send(log_line)
        print(f"Sent: {log_line}")
        
        # Wait for the 'OK' acknowledgment from the server
        result = ws.recv()
        ws.close()
        
        # Wait for a few seconds before sending the next one
        time.sleep(3) 

    except KeyboardInterrupt:
        print("\nStopping log simulator.")
        break
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5)