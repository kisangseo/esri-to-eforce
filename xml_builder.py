import xml.etree.ElementTree as ET

def get_fake_esri_data():
    return {
        "case_id": "25-22-12309",
        "status": "Closed",
        "arrival_time": "2025-11-03T15:33:00",
        "clear_time": "2025-11-03T15:37:00",
        "deputy_name": "Deputy Joe Smith",
        "address": "1234 North St",
        "city": "Baltimore City",
        "state": "MD",
        "zip": "21293",
        "activity_type": "Service Attempt Protection Order",
        "disposition": "Attempted",
        "notes": "NR LS",
        "report_taken": "Yes",
        "bwc": "Yes",
        "uof": "No"
    }

def build_event_xml(data):
    root = ET.Element("EventLog")
    rec = ET.SubElement(root, "EventRecord")

    ET.SubElement(rec, "EventNumber").text = data.get("case_id", "")
    ET.SubElement(rec, "Status").text = data.get("status", "")

    ts = ET.SubElement(rec, "Timestamps")
    ET.SubElement(ts, "Arrival").text = data.get("arrival_time", "")
    ET.SubElement(ts, "ClearTime").text = data.get("clear_time", "")

    member = ET.SubElement(rec, "Member")
    ET.SubElement(member, "Name").text = data.get("deputy_name", "")

    loc = ET.SubElement(rec, "Location")
    ET.SubElement(loc, "Address").text = data.get("address", "")
    ET.SubElement(loc, "City").text = data.get("city", "")
    ET.SubElement(loc, "State").text = data.get("state", "")
    ET.SubElement(loc, "Zip").text = data.get("zip", "")

    act = ET.SubElement(rec, "Activity")
    ET.SubElement(act, "Type").text = data.get("activity_type", "")
    ET.SubElement(act, "Disposition").text = data.get("disposition", "")
    ET.SubElement(act, "Notes").text = data.get("notes", "")

    report = ET.SubElement(rec, "Report")
    ET.SubElement(report, "ReportTaken").text = data.get("report_taken", "")
    ET.SubElement(report, "BodyWornCamera").text = data.get("bwc", "")
    ET.SubElement(report, "UseOfForce").text = data.get("uof", "")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)