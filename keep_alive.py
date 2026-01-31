from flask import Flask
from threading import Thread
import logging

# Disable Flask logging to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    # Render assigns a port automatically in the PORT env var
    # We default to 8080 if not found
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()