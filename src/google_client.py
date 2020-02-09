import json

from flask import request, jsonify, redirect

from auth_utils import key_secure, course_oauth_secure
from db import connect_db
from google_api import load_document, load_sheet


def init_db():
    with connect_db() as db:
        db("CREATE TABLE IF NOT EXISTS auth_json (email varchar(256), data LONGBLOB, course varchar(128))")


init_db()


def create_google_client(app):
    def google_help(course):
        with connect_db() as db:
            email = db("SELECT email FROM auth_json WHERE course=(%s)", [course]).fetchone()
            email = email[0] if email else ""
        return f"""
        <h3> Google Service Account </h3>
        Email address: <a href="mailto:{email}">{email}</a>
        <p>
        Share relevant Google Documents / Sheets with the above email account.
        <p>
        To configure, go to <a href="/google/{course}/config">Google Config</a>.
        """
    app.help_info.add(google_help)

    @app.route("/google/read_document", methods=["POST"])
    @key_secure
    def read_document():
        return jsonify(load_document(
            url=request.json.get("url"), doc_id=request.json.get("doc_id")
        ))

    @app.route("/google/read_spreadsheet", methods=["POST"])
    @key_secure
    def read_spreadsheet():
        return jsonify(load_sheet(
            url=request.json.get("url"),
            doc_id=request.json.get("doc_id"),
            sheet_name=request.json["sheet_name"],
        ))

    @app.route("/google/<course>/config", methods=["GET"])
    @course_oauth_secure(app)
    def google_config(course):
        return """
            Upload Google service worker JSON. This may break existing Google integrations!
            <form action="/google/{}/set_auth_json" method="post" enctype="multipart/form-data">
                <input name="data" type="file">
                <input type="submit">
            </form>
        """.format(course)

    @app.route("/google/<course>/set_auth_json", methods=["POST"])
    @course_oauth_secure(app)
    def set_auth_json(course):
        f = request.files["data"]
        f.seek(0)
        data = f.read().decode("utf-8")
        if not data.strip():
            return "Upload failed, file is blank", 403
        parsed = json.loads(data)
        email = parsed["client_email"]
        with connect_db() as db:
            db("DELETE FROM auth_json WHERE course=(%s)", [course])
            db("INSERT INTO auth_json VALUES (%s, %s, %s)", [email, data, course])
        return redirect("/")
