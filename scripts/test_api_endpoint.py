import requests
import json

def test_search():
    url = "http://localhost:8123/api/search"
    payload = {
        "query": "laptop",
        "budget": 1500,
        "user_id": "test_user",
        "cart": [],
        "skip_explanations": True
    }
    
    try:
        print(f"🚀 Sending POST request to {url}...")
        resp = requests.post(url, json=payload)
        
        print(f"📊 Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Response received!")
            print(f"   Path: {data.get('path')}")
            print(f"   Results count: {len(data.get('results', []))}")
            
            if data.get('results'):
                print(f"   Sample result: {data['results'][0]['name']}")
            else:
                print("   ⚠️ Results list is empty!")
                
            print("\nFull Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {resp.text}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure uvicorn is running on port 8123!")

if __name__ == "__main__":
    test_search()
