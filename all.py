import os
import sys

if __name__ == '__main__':
    print("Starting Unified Automation Server...")
    # Import and run the flask server from server.py
    import server
    server.app.run(debug=True, port=200000)
