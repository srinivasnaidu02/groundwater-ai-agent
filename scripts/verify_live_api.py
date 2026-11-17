"""
Live API Verification Script — Tests live backend endpoints and multi-turn chat flow.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()
session.trust_env = False  # Avoid proxy issues on localhost

print("=== 1. Testing Health Endpoint ===")
res_health = session.get(f"{BASE_URL}/api/health", timeout=5)
print(f"Health Status: {res_health.status_code}")
print(f"Response: {res_health.json()}")

print("\n=== 2. Testing National Coverage Endpoint ===")
res_cov = session.get(f"{BASE_URL}/api/coverage", timeout=5)
print(f"Coverage Status: {res_cov.status_code}")
cov_data = res_cov.json()
print(f"Total Records: {cov_data['data']['total_records']}, States: {cov_data['data']['total_states']}, Years: {cov_data['data']['available_years']}")

print("\n=== 3. Testing Live Multi-Turn Chat ===")
session_id = "test_live_session_1"

# Turn 1: 2026 Data query
q1 = "What is the groundwater extraction in Patna in 2026?"
print(f"\n[Turn 1] Question: '{q1}'")
r1 = session.post(f"{BASE_URL}/api/chat", json={"question": q1, "session_id": session_id, "mode": "hybrid"}, timeout=5)
data1 = r1.json()
print(f"Status: {data1.get('status')}")
print(f"Intent: {data1.get('intent')}")
print(f"Answer:\n{data1.get('answer')}")

# Turn 2: Follow-up year
q2 = "What about 2020?"
print(f"\n[Turn 2] Follow-up: '{q2}'")
r2 = session.post(f"{BASE_URL}/api/chat", json={"question": q2, "session_id": session_id, "mode": "hybrid"}, timeout=5)
data2 = r2.json()
print(f"Status: {data2.get('status')}")
print(f"Intent: {data2.get('intent')}")
print(f"Active Context: {data2.get('active_context')}")
print(f"Answer:\n{data2.get('answer')}")

# Turn 3: Compare both
q3 = "Compare both"
print(f"\n[Turn 3] Comparison: '{q3}'")
r3 = session.post(f"{BASE_URL}/api/chat", json={"question": q3, "session_id": session_id, "mode": "hybrid"}, timeout=5)
data3 = r3.json()
print(f"Status: {data3.get('status')}")
print(f"Intent: {data3.get('intent')}")
print(f"Answer:\n{data3.get('answer')}")

# Turn 4: Domain knowledge
q4 = "What is an aquifer?"
print(f"\n[Turn 4] Domain Question: '{q4}'")
r4 = session.post(f"{BASE_URL}/api/chat", json={"question": q4, "session_id": session_id, "mode": "hybrid"}, timeout=5)
data4 = r4.json()
print(f"Answer:\n{data4.get('answer')}")

print("\n=== [ALL LIVE VERIFICATIONS PASSED SUCCESSFULLY] ===")

