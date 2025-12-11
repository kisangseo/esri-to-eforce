from flask import Flask, request, jsonify
import logging
import os

from xml_builder import build_event_xml, get_fake_esri_data
from sftp_sender import send_to_sftp

app = Flask(__name__)

# Configure logging (printed to Azure logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load ESRI secret from Azure App Settings
WEBHOOK_SECRET = os.getenv("ESRI_SECRET")  # <-- set in Azure App Settings
print("DEBUG: ESRI_SECRET loaded as →", WEBHOOK_SECRET, flush=True)
logging.info(f"DEBUG: ESRI_SECRET loaded as → {WEBHOOK_SECRET}")


@app.post("/esri-webhook")
def esri_webhook():
    """
    Webhook endpoint that ESRI will call via HTTP POST.
    Validates a shared secret header, then converts ESRI data -> XML
    and (for now) saves it locally via send_to_sftp().
    """

    # ----- Auth check: shared secret header -----
    received_secret = request.headers.get("X-ESRI-SECRET")  # ESRI must send this header

    if WEBHOOK_SECRET and received_secret != WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        return jsonify({"error": "unauthorized"}), 401

    # ----- Parse JSON payload -----
    payload = request.get_json(silent=True) or {}
    logging.info(f"Webhook received payload: {payload}")

    # ----- Extract feature ID if present -----
    feature_id = (
        payload.get("featureId")
        or payload.get("objectId")
        or None
    )

    if not feature_id:
        logging.warning("No feature ID found in webhook payload; using fake ESRI data.")
        data = get_fake_esri_data()
    else:
        logging.info(f"Feature ID from payload: {feature_id}")
        # TODO: When Luke gives you the ESRI URL, replace this with a real REST call:
        # data = pull_esri_data(feature_id)
        data = get_fake_esri_data()

    # ----- Build XML -----
    xml_bytes = build_event_xml(data)
    filename = f"{data.get('case_id', 'unknown')}.xml"

    # ----- Send to SFTP (currently: save locally) -----
    ok = send_to_sftp(xml_bytes, filename)

    if not ok:
        # If saving fails, return 500 so ESRI could retry later
        logging.error("Failed to save XML file")
        return jsonify({"error": "failed_to_save_xml"}), 500

    return jsonify({"status": "ok", "saved_as": filename}), 200


# Azure App Service will run this via gunicorn using startup.sh
if __name__ == "__main__":
    # Handy for local debugging only
    app.run(host="0.0.0.0", port=8000, debug=True)