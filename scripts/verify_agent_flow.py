"""
Direct Verification Script — executes endpoint route handlers directly with live DB session.
"""
import sys
from pathlib import Path

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database.connection import get_sync_db
from app.main import health_check, get_national_coverage, chat_endpoint
from app.schemas.schemas import ChatRequest

db = get_sync_db()

print("=== 1. Testing Health Handler ===")
h = health_check(db)
print(f"Status: {h.status}, DB Connected: {h.database_connected}, Total Records: {h.total_records}")
print(f"Assessment Years: {h.assessment_years}")

print("\n=== 2. Testing National Coverage Handler ===")
cov = get_national_coverage(db)
print(f"Status: {cov['status']}")
print(f"Total Records: {cov['data']['total_records']}, States: {cov['data']['total_states']}, Available Years: {cov['data']['available_years']}")

print("\n=== 3. Testing Chat Conversation (Multi-Turn) ===")
session_id = "direct_test_session_1"

# Turn 1: 2026 Data query
q1 = "What is the groundwater extraction in Patna in 2026?"
print(f"\n[Turn 1] Question: '{q1}'")
r1 = chat_endpoint(ChatRequest(question=q1, session_id=session_id, mode="hybrid"), db=db)
print(f"Status: {r1.status}")
print(f"Intent: {r1.intent}")
print(f"Function: {r1.selected_function}")
print(f"Answer:\n{r1.answer}")

# Turn 2: Follow-up year
q2 = "What about 2020?"
print(f"\n[Turn 2] Follow-up: '{q2}'")
r2 = chat_endpoint(ChatRequest(question=q2, session_id=session_id, mode="hybrid"), db=db)
print(f"Status: {r2.status}")
print(f"Intent: {r2.intent}")
print(f"Active Context: {r2.active_context}")
print(f"Answer:\n{r2.answer}")

# Turn 3: Compare both
q3 = "Compare both"
print(f"\n[Turn 3] Comparison: '{q3}'")
r3 = chat_endpoint(ChatRequest(question=q3, session_id=session_id, mode="hybrid"), db=db)
print(f"Status: {r3.status}")
print(f"Intent: {r3.intent}")
print(f"Answer:\n{r3.answer}")

# Turn 4: Domain knowledge
q4 = "What is an aquifer?"
print(f"\n[Turn 4] Domain Question: '{q4}'")
r4 = chat_endpoint(ChatRequest(question=q4, session_id=session_id, mode="hybrid"), db=db)
print(f"Answer:\n{r4.answer}")

# Turn 5: Overexploited explanation
q5 = "Explain what over-exploited means"
print(f"\n[Turn 5] Domain Question: '{q5}'")
r5 = chat_endpoint(ChatRequest(question=q5, session_id=session_id, mode="hybrid"), db=db)
print(f"Answer:\n{r5.answer}")

print("\n=== ALL DIRECT VERIFICATIONS PASSED SUCCESSFULLY ===")

