"""
validate.py
Basic data quality checks on whoop.db. Run after pull_data.py.

Run:
    python3 validate.py
"""
import sqlite3
import sys

conn = sqlite3.connect("whoop.db")
cur = conn.cursor()

errors = []

# 1. Recovery scores should be between 0 and 100
cur.execute("""
    SELECT cycle_id, recovery_score FROM recovery
    WHERE recovery_score IS NOT NULL
      AND (recovery_score < 0 OR recovery_score > 100)
""")
bad_recovery = cur.fetchall()
if bad_recovery:
    errors.append(f"{len(bad_recovery)} recovery rows with out-of-range scores: {bad_recovery}")

# 2. No duplicate cycle ids
cur.execute("""
    SELECT id, COUNT(*) FROM cycles GROUP BY id HAVING COUNT(*) > 1
""")
dupes = cur.fetchall()
if dupes:
    errors.append(f"Duplicate cycle ids found: {dupes}")

# 3. Sleep efficiency should be between 0 and 100
cur.execute("""
    SELECT id, sleep_efficiency_percentage FROM sleep
    WHERE sleep_efficiency_percentage IS NOT NULL
      AND (sleep_efficiency_percentage < 0 OR sleep_efficiency_percentage > 100)
""")
bad_sleep = cur.fetchall()
if bad_sleep:
    errors.append(f"{len(bad_sleep)} sleep rows with out-of-range efficiency: {bad_sleep}")

# 4. Every recovery row should reference a cycle_id that actually exists
cur.execute("""
    SELECT r.cycle_id FROM recovery r
    LEFT JOIN cycles c ON r.cycle_id = c.id
    WHERE c.id IS NULL
""")
orphans = cur.fetchall()
if orphans:
    errors.append(f"{len(orphans)} recovery rows reference a missing cycle_id: {orphans}")

conn.close()

if errors:
    print("Data validation FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("Data validation passed: no issues found.")