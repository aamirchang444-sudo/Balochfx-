import os
import json
import hashlib
import secrets
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

LICENSE_FILE = "licenses.json"


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


LICENSE_SECRET = os.environ.get("LICENSE_SECRET", "")
OWNER_SETUP_TOKEN = os.environ.get("OWNER_SETUP_TOKEN", "")
OWNER_DEVICE_HASH = os.environ.get("OWNER_DEVICE_HASH", "")


DEFAULT_LICENSES = {
    "BFX-DEMO-2026": {
        "expires": "2026-12-31",
        "max_devices": 1,
        "devices": []
    }
}


def load_licenses():
    if not os.path.exists(LICENSE_FILE):
        save_licenses(DEFAULT_LICENSES)
        return DEFAULT_LICENSES.copy()

    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return DEFAULT_LICENSES.copy()

        return data

    except Exception:
        return DEFAULT_LICENSES.copy()


def save_licenses(data):
    temp_file = LICENSE_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(temp_file, LICENSE_FILE)


LICENSES = load_licenses()


def device_hash(device_id):
    raw = f"{LICENSE_SECRET}:{device_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_date(date_text):
    try:
        return datetime.strptime(
            date_text, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc).date()

    except (ValueError, TypeError):
        return None


def generate_license_code():
    part1 = secrets.token_hex(3).upper()
    part2 = secrets.token_hex(3).upper()

    return f"BFX-{part1}-{part2}"


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "BALOCHFX License Server"
    })


@app.post("/api/owner-hash")
def owner_hash():
    data = request.get_json(silent=True) or {}

    setup_token = str(
        data.get("setup_token", "")
    ).strip()

    device_id = str(
        data.get("device_id", "")
    ).strip()

    if not OWNER_SETUP_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Owner setup is not configured"
        }), 500

    if setup_token != OWNER_SETUP_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Invalid owner setup token"
        }), 401

    if not device_id:
        return jsonify({
            "ok": False,
            "error": "Device ID is required"
        }), 400

    if not LICENSE_SECRET:
        return jsonify({
            "ok": False,
            "error": "Server secret is not configured"
        }), 500

    return jsonify({
        "ok": True,
        "device_hash": device_hash(device_id)
    })


@app.post("/api/generate-key")
def generate_key():
    data = request.get_json(silent=True) or {}

    setup_token = str(
        data.get("setup_token", "")
    ).strip()

    if not OWNER_SETUP_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Owner setup is not configured"
        }), 500

    if setup_token != OWNER_SETUP_TOKEN:
        return jsonify({
            "ok": False,
            "error": "Unauthorized"
        }), 401

    expires = str(
        data.get("expires", "2026-12-31")
    ).strip()

    try:
        max_devices = int(
            data.get("max_devices", 1)
        )
    except (ValueError, TypeError):
        return jsonify({
            "ok": False,
            "error": "max_devices must be a number"
        }), 400

    expiry = valid_date(expires)

    if not expiry:
        return jsonify({
            "ok": False,
            "error": "Invalid expiry date. Use YYYY-MM-DD"
        }), 400

    if max_devices < 1:
        return jsonify({
            "ok": False,
            "error": "max_devices must be at least 1"
        }), 400

    code = generate_license_code()

    while code in LICENSES:
        code = generate_license_code()

    LICENSES[code] = {
        "expires": expires,
        "max_devices": max_devices,
        "devices": []
    }

    save_licenses(LICENSES)

    return jsonify({
        "ok": True,
        "code": code,
        "expires": expires,
        "max_devices": max_devices
    })


@app.post("/api/activate")
def activate():
    data = request.get_json(silent=True) or {}

    code = str(
        data.get("code", "")
    ).strip().upper()

    device_id = str(
        data.get("device_id", "")
    ).strip()

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

    device = device_hash(device_id)

    if OWNER_DEVICE_HASH and device == OWNER_DEVICE_HASH:
        return jsonify({
            "ok": True,
            "owner": True,
            "message": "BALOCHFX owner device authorized"
        })

    license_data = LICENSES.get(code)

    if not license_data:
        return jsonify({
            "ok": False,
            "error": "Invalid license code"
        }), 401

    expiry = valid_date(
        license_data.get("expires")
    )

    if not expiry:
        return jsonify({
            "ok": False,
            "error": "Invalid license configuration"
        }), 500

    today = datetime.now(
        timezone.utc
    ).date()

    if today > expiry:
        return jsonify({
            "ok": False,
            "error": "License expired"
        }), 403

    devices = license_data.setdefault(
        "devices", []
    )

    max_devices = int(
        license_data.get("max_devices", 1)
    )

    if device not in devices:

        if len(devices) >= max_devices:
            return jsonify({
                "ok": False,
                "error": "This license is already activated on another device"
            }), 403

        devices.append(device)
        save_licenses(LICENSES)

    return jsonify({
        "ok": True,
        "message": "BALOCHFX activated",
        "expires": license_data["expires"]
    })


@app.post("/api/verify")
def verify():
    data = request.get_json(silent=True) or {}

    code = str(
        data.get("code", "")
    ).strip().upper()

    device_id = str(
        data.get("device_id", "")
    ).strip()

    if not device_id:
        return jsonify({
            "ok": False,
            "error": "Device ID is required"
        }), 400

    if not LICENSE_SECRET:
        return jsonify({
            "ok": False,
            "error": "Server secret is not configured"
        }), 500

    device = device_hash(device_id)

    if OWNER_DEVICE_HASH and device == OWNER_DEVICE_HASH:
        return jsonify({
            "ok": True,
            "owner": True
        })

    if not code:
        return jsonify({
            "ok": False,
            "error": "License code is required"
        }), 400

    license_data = LICENSES.get(code)

    if not license_data:
        return jsonify({
            "ok": False,
            "error": "Invalid license"
        }), 401

    expiry = valid_date(
        license_data.get("expires")
    )

    today = datetime.now(
        timezone.utc
    ).date()

    if not expiry or today > expiry:
        return jsonify({
            "ok": False,
            "error": "License expired"
        }), 403

    devices = license_data.get(
        "devices", []
    )

    if device not in devices:
        return jsonify({
            "ok": False,
            "error": "Device is not activated"
        }), 403

    return jsonify({
        "ok": True,
        "expires": license_data["expires"]
    })


if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
