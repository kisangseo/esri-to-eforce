from datetime import datetime, timezone

def ms_to_iso(ms):
    """Convert ESRI millisecond timestamps to ISO 8601 format (UTC)."""
    if not ms:
        return ""
    try:
        # Convert milliseconds → seconds → timezone-aware datetime
        dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return ""
    
import xml.etree.ElementTree as ET

def build_event_xml(data):

    root = ET.Element("EventLog")
    record = ET.SubElement(root, "EventRecord")

    # -------- Event Header --------
    ET.SubElement(record, "EventNumber").text = data.get("Event Number", "")
    ET.SubElement(record, "Status").text = data.get("Event Status", "")

    # -------- Times --------
    timestamps = ET.SubElement(record, "Timestamps")
    ET.SubElement(timestamps, "Arrival").text = ms_to_iso(data.get("Arrival Time"))
    ET.SubElement(timestamps, "ClearTime").text = ms_to_iso(data.get("Clear Time"))

    # -------- Member --------
    member = ET.SubElement(record, "Member")
    ET.SubElement(member, "Name").text = data.get("Name", "")

    # -------- Location --------
    location = ET.SubElement(record, "Location")
    ET.SubElement(location, "Address").text = data.get("Address (address.Address)", "")
    ET.SubElement(location, "City").text = data.get("City (address.City)", "")
    ET.SubElement(location, "State").text = data.get("Region (address.Region)", "")
    ET.SubElement(location, "Zip").text = data.get("Postal Code (address.Postal)", "")

    # -------- Activity --------
    activity = ET.SubElement(record, "Activity")
    ET.SubElement(activity, "Type").text = data.get("Activity Type", "")
    ET.SubElement(activity, "Disposition").text = data.get("Service Disposition", "")
    ET.SubElement(activity, "Notes").text = data.get("testnote", "")

    # -------- Report --------
    report = ET.SubElement(record, "Report")
    ET.SubElement(report, "ReportTaken").text = data.get("Will There Be An Additional Report?", "")
    ET.SubElement(report, "BodyWornCamera").text = data.get("Was BWC Recording for the event?", "")
    ET.SubElement(report, "UseOfForce").text = data.get("Force Used or Witnessed?", "")

    # Output as XML
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes