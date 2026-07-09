# db.py
import os
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pyodbc

EASTERN_TZ = ZoneInfo("America/New_York")
GENERATED_EVENT_ACTIVITY_KEYWORDS = ("peace order", "protective order")
MAX_GENERATED_EVENT_SEQUENCE = 99999


def get_conn() -> pyodbc.Connection:
    """
    Creates a new connection to Azure SQL using a connection string stored in App Settings.
    """
    conn_str = os.environ.get("AZURE_SQL_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("Missing AZURE_SQL_CONNECTION_STRING in environment/App Settings.")
    return pyodbc.connect(conn_str)


def _is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def should_generate_event_number(data: dict) -> bool:
    """
    Return True only for Peace Order / Protective Order events that do not
    already have an ESRI-provided event number.
    """
    if not _is_blank(data.get("Event Number")):
        return False

    activity_or_type = str(data.get("Activity Type") or data.get("Type") or "").lower()
    return any(keyword in activity_or_type for keyword in GENERATED_EVENT_ACTIVITY_KEYWORDS)


def _coerce_arrival_datetime(arrival_time):
    """
    Convert an ESRI arrival timestamp to an aware datetime.

    Numeric values are treated as ESRI epoch milliseconds. ISO-like strings are
    also accepted as a safe fallback for tests/future payload changes.
    """
    if _is_blank(arrival_time):
        return None

    try:
        if isinstance(arrival_time, (int, float)) or str(arrival_time).strip().isdigit():
            return datetime.fromtimestamp(int(arrival_time) / 1000, tz=timezone.utc)

        normalized = str(arrival_time).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            logging.warning(
                "Arrival Time has no timezone; treating it as Eastern time for generated event number prefix"
            )
            return parsed.replace(tzinfo=EASTERN_TZ)
        return parsed
    except Exception:
        logging.exception(
            "Unable to parse Arrival Time for generated event number prefix; falling back to current Eastern time"
        )
        return None


def generated_event_number_prefix(arrival_time) -> str:
    """
    Build the YY-MM prefix from the event arrival time in Eastern time.
    Falls back to current Eastern time if arrival time is unavailable/unparseable.
    """
    arrival_dt = _coerce_arrival_datetime(arrival_time)
    if arrival_dt is None:
        logging.warning(
            "Arrival Time missing or invalid; using current Eastern time for generated event number prefix"
        )
        arrival_dt = datetime.now(timezone.utc)

    return arrival_dt.astimezone(EASTERN_TZ).strftime("%y-%m")


def allocate_generated_event_number(cur, arrival_time) -> str:
    """
    Allocate the next YY-MM-NNNNN generated event number inside the caller's
    transaction using SQL Server locks to avoid duplicate numbers.
    """
    prefix = generated_event_number_prefix(arrival_time)

    cur.execute(
        """
        MERGE dbo.daily_log_event_number_sequences WITH (HOLDLOCK) AS target
        USING (SELECT ? AS prefix) AS source
            ON target.prefix = source.prefix
        WHEN NOT MATCHED THEN
            INSERT (prefix, next_number) VALUES (source.prefix, 0);
        """,
        prefix,
    )

    cur.execute(
        """
        UPDATE dbo.daily_log_event_number_sequences WITH (UPDLOCK, HOLDLOCK)
            SET next_number = next_number + 1
            OUTPUT deleted.next_number
            WHERE prefix = ?;
        """,
        prefix,
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Unable to allocate generated event number for prefix {prefix}")

    sequence_number = int(row[0])
    if sequence_number > MAX_GENERATED_EVENT_SEQUENCE:
        raise RuntimeError(f"Generated event number sequence exhausted for prefix {prefix}")

    return f"{prefix}-{sequence_number:05d}"


def insert_esri_event(data: dict) -> None:
    """
    Always insert the ESRI webhook payload into Azure SQL.
    Raises on failure (so caller can block EFORCE send).
    """
    # --- Map ESRI payload fields (store exactly what ESRI gives you) ---
    arrival_time = data.get("Arrival Time")
    clear_time = data.get("Clear Time")
    logging.info(f"ESRI payload keys: {list(data.keys())}")
    name = data.get("Name")

    event_number = data.get("Event Number")
    event_status = data.get("Event Status")
    activity_type = data.get("Activity Type")
    notes = data.get("Notes or Narrative")
    radio_id = data.get("radio_id")

    address = (
        data.get("Address (address.Address)")
        or data.get("Block Number")
        
    )
    city = data.get("City (address.City)")
    state = data.get("Region (address.Region)")
    postal_code = data.get("Postal Code (address.Postal)")

    bwc = data.get("Was BWC Recording for the event?")
    force_used = data.get("Force Used or Witnessed?")
    additional_report = data.get("Will There Be An Additional Report?")
    department_cell = data.get("Department Cell")
    sequence = data.get("Sequence")
    email = data.get("email")
    case_number = data.get("Case Number")
    civil_respondent = data.get("Civil Respondent")
    civil_service_disposition = data.get("Civil Process Service Disposition")
    describe_new_info = data.get("Describe the New Information")

    raw_payload = json.dumps(data, ensure_ascii=False)

    sql = """
    INSERT INTO dbo.esri_events (
        event_number, generated_event_number, name, radio_id, 
        arrival_time, clear_time,
        event_status, activity_type, notes_or_narrative,
        address, city, state, postal_code,
        bwc_recording, force_used, additional_report,
        department_cell, sequence, email, case_number, civil_respondent, civil_service_disposition, describe_new_info,
        raw_payload
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                generated_event_number = None
                if should_generate_event_number(data):
                    generated_event_number = allocate_generated_event_number(cur, arrival_time)

                params = (
                    event_number, generated_event_number, name, radio_id, 
                    arrival_time, clear_time,
                    event_status, activity_type, notes,
                    address, city, state, postal_code,
                    bwc, force_used, additional_report, department_cell, sequence, email, case_number, civil_respondent, civil_service_disposition, describe_new_info,
                    raw_payload
                )
                cur.execute(sql, params)
                conn.commit()
        logging.info(
            "Inserted ESRI event into Azure SQL (event_number=%s, generated_event_number=%s)",
            event_number,
            generated_event_number,
        )
    except Exception:
        logging.exception("FAILED inserting ESRI event into Azure SQL")
        raise
