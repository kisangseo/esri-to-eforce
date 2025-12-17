# db.py
import os
import json
import logging
import pyodbc


def get_conn() -> pyodbc.Connection:
    """
    Creates a new connection to Azure SQL using a connection string stored in App Settings.
    """
    conn_str = os.environ.get("AZURE_SQL_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("Missing AZURE_SQL_CONNECTION_STRING in environment/App Settings.")
    return pyodbc.connect(conn_str)


def insert_esri_event(data: dict) -> None:
    """
    Always insert the ESRI webhook payload into Azure SQL.
    Raises on failure (so caller can block EFORCE send).
    """
    # --- Map ESRI payload fields (store exactly what ESRI gives you) ---
    arrival_time = data.get("Arrival Time")
    clear_time = data.get("Clear Time")
    logging.info(f"ESRI payload keys: {list(data.keys())}")
    name = data.get("name")

    event_number = data.get("Event Number")
    event_status = data.get("Event Status")
    activity_type = data.get("Activity Type")
    notes = data.get("Notes or Narrative")

    address = data.get("Address (address.Address)")
    city = data.get("City (address.City)")
    state = data.get("Region (address.Region)")
    postal_code = data.get("Postal Code (address.Postal)")

    bwc = data.get("Was BWC Recording for the event?")
    force_used = data.get("Force Used or Witnessed?")
    additional_report = data.get("Will There Be An Additional Report?")

    raw_payload = json.dumps(data, ensure_ascii=False)

    sql = """
    INSERT INTO esri_events (
        event_number, name,
        arrival_time, clear_time,
        event_status, activity_type, notes_or_narrative,
        address, city, state, postal_code,
        bwc_recording, force_used, additional_report,
        raw_payload
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    params = (
        event_number, name, 
        arrival_time, clear_time,
        event_status, activity_type, notes,
        address, city, state, postal_code,
        bwc, force_used, additional_report,
        raw_payload
    )

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
        logging.info("Inserted ESRI event into Azure SQL (event_number=%s)", event_number)
    except Exception:
        logging.exception("FAILED inserting ESRI event into Azure SQL")
        raise
