import os
import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


LICENSE_SECRET = os.environ.get("LICENSE_SECRET", "")

# Demo licenses.
# Inhe baad mein server-side database se replace karenge.
LICENSES = {
    "BFX-DEMO-2026": {
        "expires": "2026-12-31",
        "max_devices": 1,
        "devices": []
    }
}


def device_hash(device_id):
    raw = f"{LICENSE_SECRET}:{device_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_date(date_text):
    try:
        return datetime.strptime(
            date_text, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc).date()
    except ValueError:
        return None


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "BALOCHFX License Server"
    })


@app.post("/api/activate")
def activate():
    data = request.get_json(silent=True) or {}

    code = str(data.get("code", "")).strip().upper()
    device_id = str(data.get("device_id", "")).strip()

    if not code or not device_id:
        return jsonify({
            "ok": False,
            "error": "License code and device ID are required"
        }), 400

    if not LICENSE_SECRET:
        return jsonify({
            "ok": False,
            "error": "Server secret is not configured"
        }), 500

    license_data = LICENSES.get(code)

    if not license_data:
        return jsonify({
            "ok": False,
            "error": "Invalid license code"
        }), 401

    expiry = valid_date(license_data["expires"])

    if not expiry:
        return jsonify({
            "ok": False,
            "error": "Invalid license configuration"
        }), 500

    today = datetime.now(timezone.utc).date()

    if today > expiry:
        return jsonify({
            "ok": False,
            "error": "License expired"
        }), 403

    device = device_hash(device_id)

    if device not in license_data["devices"]:
        if len(license_data["devices"]) >= license_data["max_devices"]:
            return jsonify({
                "ok": False,
                "error": "This license is already activated on another device"
            }), 403

        license_data["devices"].append(device)

    return jsonify({
        "ok": True,
        "message": "BALOCHFX activated",
        "expires": license_data["expires"]
    })


@app.post("/api/verify")
def verify():
    data = request.get_json(silent=True) or {}

    code = str(data.get("code", "")).strip().upper()
    device_id = str(data.get("device_id", "")).strip()

    if not code or not device_id:
        return jsonify({
            "ok": False,
            "error": "License code and device ID are required"
        }), 400

    license_data = LICENSES.get(code)

    if not license_data:
        return jsonify({
            "ok": False,
            "error": "Invalid license"
        }), 401

    expiry = valid_date(license_data["expires"])
    today = datetime.now(timezone.utc).date()

    if not expiry or today > expiry:
        return jsonify({
            "ok": False,
            "error": "License expired"
        }), 403

    device = device_hash(device_id)

    if device not in license_data["devices"]:
        return jsonify({
            "ok": False,
            "error": "Device is not activated"
        }), 403

    return jsonify({
        "ok": True,
        "expires": license_data["expires"]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port
    )
