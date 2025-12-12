import json
from xml_builder import build_event_xml
import os

# Load JSON from file
with open("test_payload.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Build XML bytes
xml_bytes = build_event_xml(data)

# Output to console
print("===== GENERATED XML FROM REAL JSON =====")
print(xml_bytes.decode())

# Save to outgoing_xml folder
out_dir = "outgoing_xml"
os.makedirs(out_dir, exist_ok=True)

output_path = os.path.join(out_dir, "real_test_output.xml")
with open(output_path, "wb") as f:
    f.write(xml_bytes)

print("\nXML saved to:", output_path)
