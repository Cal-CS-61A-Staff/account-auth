import json

from flask import request, jsonify

from auth_utils import key_secure, oauth_secure
from db import connect_db
from google_api import load_document, load_sheet


def create_google_client(app):
    def google_help():
        with connect_db() as db:
            email = db("SELECT email FROM auth_json").fetchone()[0]
        return f"""
        <h3> Google Service Account </h3>
        Email address: <a href="mailto:{email}">{email}</a>
        <p>
        Share relevant Google Documents / Sheets with the above email account.
        <p>
        To configure, go to <a href="/google/config">Google Config</a>.
        """
    app.help_info.add(google_help)

    @app.route("/google/read_document", methods=["POST"])
    @key_secure(app)
    def read_document():
        return jsonify(load_document(
            url=request.json.get("url"), doc_id=request.json.get("doc_id")
        ))

    @app.route("/google/read_spreadsheet", methods=["POST"])
    @key_secure(app)
    def read_spreadsheet():
        return jsonify(load_sheet(
            url=request.json.get("url"),
            doc_id=request.json.get("doc_id"),
            sheet_name=request.json["sheet_name"],
        ))

    @app.route("/google/config", methods=["GET"])
    @oauth_secure(app)
    def google_config():
        return """
            Upload Google service worker JSON. This may break existing Google integrations!
            <form action="/google/set_auth_json" method="post" enctype="multipart/form-data">
                <input name="data" type="file">
                <input type="submit">
            </form>
        """

    @app.route("/google/set_auth_json", methods=["POST"])
    @oauth_secure(app)
    def set_auth_json():
        f = request.files["data"]
        f.seek(0)
        data = f.read().decode("utf-8")
        if not data.strip():
            return "Upload failed, file is blank", 403
        parsed = json.loads(data)
        email = parsed["client_email"]
        with connect_db() as db:
            db("DROP TABLE IF EXISTS auth_json")
            db("CREATE TABLE auth_json (email varchar(256), data LONGBLOB)")
            db("INSERT INTO auth_json VALUES (%s, %s)", [email, data])
        return "Success!"
