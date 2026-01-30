import requests
import time
import json

BASE_URL = "http://localhost:8123/api/analytics"

def wait_for_server(url, timeout=30):
    print(f"⏳ Waiting for server at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get("http://localhost:8123/api/health")
            print("   ✅ Server is up!")
            return True
        except requests.ConnectionError:
            time.sleep(1)
            print(".", end="", flush=True)
    print("\n   ❌ Server timed out.")
    return False

def test_analytics_flow():
    if not wait_for_server(BASE_URL):
        return

    print("🧪 Testing Analytics API Flow...")
    
    # 1. Start Session
    print("\n1️⃣ Starting Session...")
    try:
        response = requests.post(f"{BASE_URL}/session", json={
            "user_id": "test_script_user",
            "query": "gaming mouse",
            "budget": 100,
            "path": "fast"
        })
        response.raise_for_status()
        session_id = response.json().get("session_id")
        print(f"   ✅ Session created: {session_id}")
    except Exception as e:
        print(f"   ❌ Failed to create session: {e}")
        return

    # 2. Track Impressions
    print("\n2️⃣ Tracking Impressions...")
    try:
        products = [
            {"product_id": "p1", "price": 50},
            {"product_id": "p2", "price": 120},  # Over budget
            {"product_id": "p3", "price": 80}
        ]
        response = requests.post(f"{BASE_URL}/track/impression", json={
            "session_id": session_id,
            "products": products,
            "budget": 100,
            "query": "gaming mouse"
        })
        response.raise_for_status()
        result = response.json()
        print(f"   ✅ Impressions tracked. Compliance: {result.get('compliance_rate')}%")
    except Exception as e:
        print(f"   ❌ Failed to track impressions: {e}")

    # 3. Track Click
    print("\n3️⃣ Tracking Click...")
    try:
        response = requests.post(f"{BASE_URL}/track/click", json={
            "session_id": session_id,
            "product_id": "p1",
            "position": 0,
            "price": 50,
            "budget": 100
        })
        response.raise_for_status()
        print(f"   ✅ Click tracked: {response.json()}")
    except Exception as e:
        print(f"   ❌ Failed to track click: {e}")

    # 4. Check Dashboard
    print("\n4️⃣ Checking Dashboard...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard?hours=1")
        response.raise_for_status()
        dash = response.json()
        clicks = dash['engagement']['ctr']['clicks']
        print(f"   ✅ Dashboard retrieved. Total clicks in last hour: {clicks}")
        if clicks > 0:
            print("   ✅ Data is flowing correctly!")
        else:
            print("   ⚠️ Data might not be persisted or read correctly immediately (check file system)")
    except Exception as e:
        print(f"   ❌ Failed to get dashboard: {e}")

    # 5. End Session
    print("\n5️⃣ Ending Session...")
    try:
        requests.post(f"{BASE_URL}/session/{session_id}/end")
        print("   ✅ Session ended")
    except Exception as e:
        print(f"   ❌ Failed to end session: {e}")

if __name__ == "__main__":
    test_analytics_flow()
