import os
import logging

def send_to_sftp(xml_bytes, filename):
    folder = "outgoing_xml"

    if not os.path.exists(folder):
        os.mkdir(folder)

    local_path = os.path.join(folder, filename)

    try:
        with open(local_path, "wb") as f:
            f.write(xml_bytes)

        logging.info(f"[TEMP] Saved XML to: {local_path}")
        return True
    except Exception as e:
        logging.error(f"ERROR saving XML locally: {e}")
        return False