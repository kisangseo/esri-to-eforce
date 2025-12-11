import json
from xml_builder import build_event_xml

# Load fake payload
with open("test_payload.json", "r") as f:
    data = json.load(f)

# Build XML
xml_bytes = build_event_xml(data)
xml_string = xml_bytes.decode("utf-8")

# Print XML to console
print("===== GENERATED XML =====")
print(xml_string)

# Save XML to folder
output_path = "outgoing_xml/test_output.xml"

import os
if not os.path.exists("outgoing_xml"):
    os.mkdir("outgoing_xml")

with open(output_path, "w", encoding="utf-8") as f:
    f.write(xml_string)

print(f"\nXML saved to: {output_path}")
