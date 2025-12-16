from flask import Flask, request, jsonify
import logging
import os
import requests

from xml_builder import build_event_xml
from sftp_sender import send_to_sftp

app = Flask(__name__)
ESRI_LAYER_URL = "https://services.arcgis.com/njFNhDsUCentVYJW/arcgis/rest/services/service_000dd40ddcd24144b9eb6b31a68ff15e/FeatureServer/0"

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
    data = payload
    logging.info(f"Webhook received payload: {payload}")

    feature_id = payload.get("featureId") or payload.get("objectId")

    if feature_id:
        logging.info(f"Feature ID received: {feature_id}")
    else:
        logging.warning("No feature ID found – would use fake ESRI data here")




    # -----------------------------
    # Build XML from payload
    # -----------------------------
    xml_data = build_event_xml(data)

    logging.info("XML successfully generated")

    # -----------------------------
    # Send XML to EFORCE via SFTP
    # -----------------------------
    filename = "esri_event.xml"

    send_to_sftp(xml_data, filename)

    logging.info("XML successfully sent to SFTP")

    return jsonify({"status": "ok"}), 200


