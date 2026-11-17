"""
Verify live API responses for the 10 mandatory test queries.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_live_chat():
    sess_id = "test_live_session_101"

    test_queries = [
        ("1. 'hii'", "hii", False),
        ("2. 'hello'", "hello", False),
        ("3. 'how are you?'", "how are you?", False),
        ("4. 'thank you'", "thank you", False),
        ("5. 'what can you do?'", "what can you do?", False),
        ("6. 'what is an aquifer?'", "what is an aquifer?", False),
        ("7. 'explain groundwater recharge'", "explain groundwater recharge", False),
        ("8. 'what is groundwater extraction in Patna in 2022?'", "what is groundwater extraction in Patna in 2022?", True),
        ("9. 'what about 2025?'", "what about 2025?", True),
        ("10. 'compare both'", "compare both", True),
    ]

    print("=" * 70)
    print("LIVE CHAT API VERIFICATION (http://127.0.0.1:8000/api/chat)")
    print("=" * 70)

    for label, q, expects_db in test_queries:
        payload = {"question": q, "session_id": sess_id, "mode": "hybrid"}
        r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
        assert r.status_code == 200, f"Failed on {label}: {r.status_code} {r.text}"
        data = r.json()

        func = data.get("selected_function")
        ans = data.get("answer", "")
        intent = data.get("intent")

        print(f"\n{label}")
        print(f"  Input: {q}")
        print(f"  Intent: {intent}")
        print(f"  Function called: {func}")
        print(f"  Answer preview: {ans[:120]}...")

        if not expects_db:
            assert func is None, f"Expected NO db function for '{q}', got {func}"
            assert "Verified data for this location" not in ans, f"Got DB error for conversational query '{q}'"
        else:
            assert func is not None, f"Expected DB function for '{q}', got None"
            assert "Verified data for this location" not in ans, f"Got DB error for verified query '{q}'"

    print("\n" + "=" * 70)
    print("ALL 10 MANDATORY LIVE TEST QUERIES PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_live_chat()

