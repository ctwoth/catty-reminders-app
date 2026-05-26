#!/usr/bin/env python3
import subprocess
import threading
import logging
from flask import Flask, request, jsonify


#paths
APP_HOME = "/home/dev/catty-reminders-app"
DEPLOY_ENV_FILE = "/etc/catty-app-env"
SERVICE_NAME = "catty"
LOG_FILE = "/home/dev/deploy.log"

#logs
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)


def perform_update(commit_hash: str):
    """Update code and rerun service"""
    try:
        subprocess.run(
            ["git", "-C", APP_HOME, "fetch", "--all"],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", APP_HOME, "reset", "--hard", commit_hash],
            check=True,
            capture_output=True
        )
        # 3. Записать хеш коммита в файл окружения (будет подхвачен сервисом)
        with open(DEPLOY_ENV_FILE, "w") as f:
            f.write(f"DEPLOY_REF={commit_hash}\n")
        # 4. Перезапустить веб-приложение
        subprocess.run(
            ["sudo", "systemctl", "restart", SERVICE_NAME],
            check=True,
            capture_output=True
        )
        logging.info(f"Updates to commit {commit_hash}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error while comand run: {e.stderr.decode() if e.stderr else str(e)}")

    except Exception as e:
        logging.error(f"Error: {e}")

@app.route("/", methods=["POST"])


def webhook():
    """GitHub Webhook logic"""
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        payload = request.get_json()
        commit_sha = payload.get("after") if payload else None

        if commit_sha and commit_sha != "0" * 40:
            threading.Thread(target=perform_update, args=(commit_sha,), daemon=True).start()
            return jsonify({"status": "accepted"}), 202

    # rest actions
    return jsonify({"status": "ignored"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
