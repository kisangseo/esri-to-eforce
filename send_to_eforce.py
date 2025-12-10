import logging
import os
import xml.etree.ElementTree as ET

# ---------------------------------------
# Setup Logging
# ---------------------------------------
logging.basicConfig(
    filename="bcso_esri_to_eforce.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------------------
# Hardcoded "fake ESRI data" for prototype
# Replace this with real ESRI REST call later
# ---------------------------------------
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

# ---------------------------------------
# Build XML based on your schema
# (Matches your uploaded sample exactly)
# ---------------------------------------
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

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes

# ---------------------------------------
# TEMPORARY "send" — saves XML locally
# Will be replaced with SFTP upload later
# ---------------------------------------
def send_to_sftp(xml_bytes, filename):
    folder = "outgoing_xml"

    if not os.path.exists(folder):
        os.mkdir(folder)

    local_path = os.path.join(folder, filename)

    try:
        with open(local_path, "wb") as f:
            f.write(xml_bytes)

        logging.info(f"[TEMP] Saved XML to: {local_path}")
        print(f"[TEMP] Saved XML to: {local_path}")
        return True

    except Exception as e:
        logging.error(f"ERROR writing file locally: {e}")
        print(f"[ERROR] Could not save XML locally: {e}")
        return False

# ---------------------------------------
# MAIN EXECUTION
# ---------------------------------------
if __name__ == "__main__":
    logging.info("Starting ESRI → XML → EFORCE prototype.")

    # Step 1: Get data (fake for now)
    data = get_fake_esri_data()
    logging.info("Loaded fake ESRI data.")

    # Step 2: Build XML file
    xml_bytes = build_event_xml(data)
    filename = f"{data['case_id']}.xml"
    logging.info(f"XML built for case {data['case_id']}.")

    # Step 3: Save file locally (SFTP later)
    send_to_sftp(xml_bytes, filename)

    logging.info("Prototype script finished.")
    print("Done.")
