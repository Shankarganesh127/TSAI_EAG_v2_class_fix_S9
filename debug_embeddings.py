import requests
import json

def check_server(base_url, name):
    print(f"\n--- Checking {name} ({base_url}) ---")
    
    # List models
    try:
        print(f"Listing models at {base_url}/api/tags...")
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        print(f"Tags Status: {resp.status_code}")
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            print(f"Available models: {models}")
            if "nomic-embed-text:latest" in models:
                print("✅ nomic-embed-text:latest is available!")
            else:
                print("❌ nomic-embed-text:latest is NOT found.")
        else:
            print(f"Tags Error: {resp.text}")
    except Exception as e:
        print(f"Tags Exception: {e}")

    # Try embedding
    try:
        print(f"Testing embedding at {base_url}/api/embeddings...")
        resp = requests.post(
            f"{base_url}/api/embeddings", 
            json={"model": "nomic-embed-text:latest", "prompt": "test"}, 
            timeout=5
        )
        print(f"Embed Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ Embedding success!")
        else:
            print(f"❌ Embed Error: {resp.text}")
    except Exception as e:
        print(f"Embed Exception: {e}")

check_server("http://localhost:8080", "Port 8080")
check_server("http://localhost:11434", "Port 11434")
