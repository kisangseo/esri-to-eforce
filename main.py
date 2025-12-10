from flask import Flask, request, jsonify
import logging
from xml_builder import build_event_xml, get_fake_esri_data
from sftp_sender import send_to_sftp

app = Flask(__name__)

# Configure logging (printed to Azure logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# OPTIONAL SECRET so only ESRI can send to your webhook
WEBHOOK_SECRET = "my-secret-token"  # replace later

@app.post("/esri-webhook")
def esri_webhook():
    # Validate secret if ESRI sends one
    received_secret = request.headers.get("X-Webhook-Token")
    if WEBHOOK_SECRET and received_secret != WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        return jsonify({"error": "unauthorized"}), 401

    payload = request.json
    logging.info(f"Webhook received: {payload}")

    # Extract feature ID if present
    feature_id = payload.get("featureId") or payload.get("objectId") or None

    if not feature_id:
        logging.warning("No feature ID found in webhook payload")
        # For now, use fake ESRI data
        data = get_fake_esri_data()
    else:
        # When Luke gives you the ESRI URL, replace this call:
        # data = pull_esri_data(feature_id)
        data = get_fake_esri_data()

    # Convert to XML
    xml_bytes = build_event_xml(data)
    filename = f"{data.get('case_id', 'unknown')}.xml"

    # Save locally for now
    send_to_sftp(xml_bytes, filename)

    return jsonify({"status": "ok", "saved_as": filename}), 200

# Azure App Service will call app.run using gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)