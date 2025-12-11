from flask import Flask, request, jsonify
import logging
import os
import requests

from xml_builder import build_event_xml, get_fake_esri_data
from sftp_sender import send_to_sftp

ESRI_LAYER_URL = (
    "https://services.arcgis.com/njFNhDsUCentVYJW/arcgis/rest/services/"
    "service_000dd40ddcd24144b9eb6b31a68ff15e/FeatureServer/0"
)

app = Flask(__name__)

# Configure logging (printed to Azure logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load ESRI secret from Azure App Settings
WEBHOOK_SECRET = os.getenv("ESRI_SECRET")
print("DEBUG: ESRI_SECRET loaded as →", WEBHOOK_SECRET, flush=True)
logging.info(f"DEBUG: ESRI_SECRET loaded as → {WEBHOOK_SECRET}")


@app.post("/esri-webhook")
def esri_webhook():
    """
    ESRI sends POST → we validate → convert ESRI JSON → XML → send to SFTP.
    """

    # ------------------------------
    # Validate shared webhook secret
    # ------------------------------
    received_secret = request.headers.get("X-ESRI-SECRET")

    if WEBHOOK_SECRET and received_secret != WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        return jsonify({"error": "unauthorized"}), 401

    # ------------------------------
    # Parse incoming JSON
    # ------------------------------
    payload = request.get_json(silent=True) or {}
    logging.info(f"Webhook received payload: {payload}")

    # ESRI webhook *may* provide an objectId or featureId
    feature_id = (
        payload.get("featureId")
        or payload.get("objectId")
        or None
    )

    if not feature_id:
        logging.warning("No feature ID found – using fake ESRI data.")
        data = get_fake_esri_data()
    else:
        logging.info(f"Feature ID received: {feature_id}")

        # TODO: Replace with real REST call after Luke provides final schema.
        data = get_fake_esri_data()

    # ------------------------------------------------------
    # Convert ESRI → XML
    # ------------------------------------------------------
    xml_bytes = build_event_xml(data)

    # IMPORTANT:
    # Now saving using the **Event Number** field from your XML mapping
    filename = f"{data.get('event_number', 'unknown')}.xml"

    # ------------------------------------------------------
    # Save a readable XML copy locally (debugging)
    # ------------------------------------------------------
    try:
        with open("test_output.xml", "wb") as f:
            f.write(xml_bytes)
        logging.info("test_output.xml saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save test_output.xml: {e}")

    # ------------------------------------------------------
    # Send to SFTP (currently saves locally in outgoing_xml/)
    # ------------------------------------------------------
    ok = send_to_sftp(xml_bytes, filename)

    if not ok:
        logging.error("Failed to save XML file")
        return jsonify({"error": "failed_to_save_xml"}), 500

    return jsonify({"status": "ok", "saved_as": filename}), 200


# Used only when running locally
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)