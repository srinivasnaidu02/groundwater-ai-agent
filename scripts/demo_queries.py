import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database.connection import init_db, get_sync_db
from app.nlp.query_parser import parse_question
from app.agent.planner import QueryPlanner

init_db()
db = get_sync_db()
planner = QueryPlanner(db)

demo_queries = [
    "What is the groundwater extraction in Patna district in 2022?",
    "Show annual groundwater recharge in Bihar.",
    "Which districts in Bihar are over-exploited?",
    "What is the stage of groundwater extraction in Gaya?",
    "Compare groundwater extraction between Patna and Gaya.",
    "What assessment years are available?",
    "What is the groundwater extraction in Patna in 2023?",
    "What is the groundwater level in Patna?",
    "Show groundwater in Bihar"
]

print("="*80)
print("GROUNDWATER AI AGENT — END-TO-END DEMONSTRATION")
print("="*80)

for idx, q in enumerate(demo_queries, 1):
    parsed = parse_question(q)
    res = planner.plan_and_execute(parsed)
    print(f"\n[DEMO {idx}] QUESTION: {q}")
    print(f"  -> Detected Intent: {res.get('intent')}")
    print(f"  -> Selected Function: {res.get('selected_function')}()")
    print(f"  -> Parameters: {res.get('parameters')}")
    print(f"  -> Status: {res.get('status')}")
    print(f"  -> Execution Time: {res.get('execution_time_ms')} ms")
    print(f"  -> Answer: {res.get('answer')}")

db.close()

