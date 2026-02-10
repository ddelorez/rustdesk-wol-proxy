from flask import Flask, request, jsonify
import logging
from logging.handlers import RotatingFileHandler
import wakeonlan  # we'll pip install wakeonlan if not already present
import os

app = Flask(__name__)

# ------------------------------
# Configuration
# ------------------------------
API_KEY = os.getenv("WOL_API_KEY", "changeme-please-set-this")  # CHANGE THIS
ALLOWED_IDS = {
    "123456789": "AA:BB:CC:DD:EE:FF",   # RustDesk ID → MAC
    "987654321": "11:22:33:44:55:66",
    # Add your real mappings here
}

LOG_FILE = "/var/log/rustdesk-wol-proxy.log"
BROADCAST_IP = "10.10.10.255"

# ------------------------------
# Logging setup
# ------------------------------
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# ------------------------------
# Routes
# ------------------------------
@app.route('/wake', methods=['GET'])
def wake():
    client_api_key = request.args.get('key')
    rustdesk_id = request.args.get('id')

    if not rustdesk_id:
        app.logger.warning("Missing id parameter")
        return jsonify({"error": "Missing id parameter"}), 400

    if client_api_key != API_KEY:
        app.logger.warning(f"Invalid API key attempt for ID {rustdesk_id}")
        return jsonify({"error": "Invalid API key"}), 403

    mac = ALLOWED_IDS.get(rustdesk_id)
    if not mac:
        app.logger.info(f"No MAC registered for ID {rustdesk_id}")
        return jsonify({"error": "No MAC address registered for this ID"}), 404

    try:
        wakeonlan.send_magic_packet(mac, ip=BROADCAST_IP)
        app.logger.info(f"WOL packet sent to {mac} (ID: {rustdesk_id})")
        return jsonify({
            "status": "success",
            "message": f"Wake-on-LAN packet sent to {mac}",
            "id": rustdesk_id
        }), 200
    except Exception as e:
        app.logger.error(f"Failed to send WOL packet to {mac}: {str(e)}")
        return jsonify({"error": "Failed to send magic packet"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)  # debug only during dev