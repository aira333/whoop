"""
pull_data.py
Pulls cycles, recovery, sleep, and workout data from the WHOOP API
and stores it in a local SQLite database (whoop.db).

Run after whoop_auth.py has created tokens.json:
    python3 pull_data.py
"""
import sqlite3
import requests
from whoop_auth import get_valid_access_token

BASE_URL = "https://api.prod.whoop.com/developer/v1"
DB_PATH = "whoop.db"


def get_headers():
    token = get_valid_access_token()
    return {"Authorization": f"Bearer {token}"}


def paginate(endpoint, headers, limit=25):
    """Generic paginator for WHOOP v1 endpoints (they use next_token)."""
    records = []
    next_token = None
    while True:
        params = {"limit": limit}
        if next_token:
            params["nextToken"] = next_token
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        next_token = data.get("next_token")
        if not next_token:
            break
    return records


def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY,
            start TEXT, "end" TEXT,
            score_state TEXT,
            strain REAL, kilojoule REAL,
            average_heart_rate INTEGER, max_heart_rate INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recovery (
            cycle_id INTEGER,
            sleep_id INTEGER,
            score_state TEXT,
            recovery_score INTEGER,
            resting_heart_rate REAL,
            hrv_rmssd_milli REAL,
            spo2_percentage REAL,
            skin_temp_celsius REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep (
            id INTEGER PRIMARY KEY,
            start TEXT, "end" TEXT,
            score_state TEXT,
            total_in_bed_time_milli INTEGER,
            total_awake_time_milli INTEGER,
            total_light_sleep_time_milli INTEGER,
            total_slow_wave_sleep_time_milli INTEGER,
            total_rem_sleep_time_milli INTEGER,
            sleep_performance_percentage REAL,
            sleep_efficiency_percentage REAL,
            respiratory_rate REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY,
            start TEXT, "end" TEXT,
            sport_name TEXT,
            score_state TEXT,
            strain REAL,
            average_heart_rate INTEGER,
            max_heart_rate INTEGER,
            kilojoule REAL,
            distance_meter REAL
        )
    """)
    conn.commit()


def upsert(conn, table, columns, rows):
    if not rows:
        print(f"No new rows for {table}")
        return
    placeholders = ",".join("?" for _ in columns)
    col_str = ",".join(f'"{c}"' for c in columns)
    conn.executemany(
        f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    print(f"Upserted {len(rows)} rows into {table}")


def pull_cycles(conn, headers):
    records = paginate("/cycle", headers)
    rows = []
    for r in records:
        score = r.get("score") or {}
        rows.append((
            r["id"], r.get("start"), r.get("end"), r.get("score_state"),
            score.get("strain"), score.get("kilojoule"),
            score.get("average_heart_rate"), score.get("max_heart_rate"),
        ))
    upsert(conn, "cycles",
           ["id", "start", "end", "score_state", "strain", "kilojoule",
            "average_heart_rate", "max_heart_rate"], rows)


def pull_recovery(conn, headers):
    records = paginate("/recovery", headers)
    rows = []
    for r in records:
        score = r.get("score") or {}
        rows.append((
            r.get("cycle_id"), r.get("sleep_id"), r.get("score_state"),
            score.get("recovery_score"), score.get("resting_heart_rate"),
            score.get("hrv_rmssd_milli"), score.get("spo2_percentage"),
            score.get("skin_temp_celsius"),
        ))
    upsert(conn, "recovery",
           ["cycle_id", "sleep_id", "score_state", "recovery_score",
            "resting_heart_rate", "hrv_rmssd_milli", "spo2_percentage",
            "skin_temp_celsius"], rows)


def pull_sleep(conn, headers):
    records = paginate("/activity/sleep", headers)
    rows = []
    for r in records:
        score = r.get("score") or {}
        stage = score.get("stage_summary") or {}
        rows.append((
            r["id"], r.get("start"), r.get("end"), r.get("score_state"),
            stage.get("total_in_bed_time_milli"),
            stage.get("total_awake_time_milli"),
            stage.get("total_light_sleep_time_milli"),
            stage.get("total_slow_wave_sleep_time_milli"),
            stage.get("total_rem_sleep_time_milli"),
            score.get("sleep_performance_percentage"),
            score.get("sleep_efficiency_percentage"),
            score.get("respiratory_rate"),
        ))
    upsert(conn, "sleep",
           ["id", "start", "end", "score_state", "total_in_bed_time_milli",
            "total_awake_time_milli", "total_light_sleep_time_milli",
            "total_slow_wave_sleep_time_milli", "total_rem_sleep_time_milli",
            "sleep_performance_percentage", "sleep_efficiency_percentage",
            "respiratory_rate"], rows)


def pull_workouts(conn, headers):
    records = paginate("/activity/workout", headers)
    rows = []
    for r in records:
        score = r.get("score") or {}
        rows.append((
            r["id"], r.get("start"), r.get("end"), r.get("sport_name"),
            r.get("score_state"), score.get("strain"),
            score.get("average_heart_rate"), score.get("max_heart_rate"),
            score.get("kilojoule"), score.get("distance_meter"),
        ))
    upsert(conn, "workouts",
           ["id", "start", "end", "sport_name", "score_state", "strain",
            "average_heart_rate", "max_heart_rate", "kilojoule",
            "distance_meter"], rows)


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    headers = get_headers()

    pull_cycles(conn, headers)
    pull_recovery(conn, headers)
    pull_sleep(conn, headers)
    pull_workouts(conn, headers)

    conn.close()
    print(f"\nDone. Data stored in {DB_PATH}")


if __name__ == "__main__":
    main()