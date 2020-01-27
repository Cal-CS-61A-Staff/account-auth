import json

from flask import request, jsonify

from auth_utils import key_secure, oauth_secure
from db import connect_db
from google_api import load_document


def create_piazza_client(app):
    def piazza_help():
        with connect_db() as db:
            student_email, staff_email, course_id = db(
                "SELECT student_user, staff_user, course_id FROM piazza_config"
            ).fetchone()
        return f"""
        <h3> Piazza Service Accounts </h3>
        Student email address: <a href="mailto:{student_email}">{student_email}</a>
        <p>
        Staff email address: <a href="mailto:{staff_email}">{staff_email}</a>
        <p>
        Piazza course: <a href="https://piazza.com/class/{course_id}">https://piazza.com/class/{course_id}</a>
        <p>
        Enroll these accounts on the latest course Piazza.
        <p>
        To configure, go to <a href="/piazza/config">Piazza Config</a>.
        """

    app.help_info.add(piazza_help)

    @app.route("/piazza/action/<action>", methods=["POST"])
    @key_secure(app)
    def perform_action(action):
        return jsonify(
            load_document(
                url=request.json.get("url"), doc_id=request.json.get("doc_id")
            )
        )

    @app.route("/piazza/config", methods=["GET"])
    @oauth_secure(app)
    def piazza_config():
        return """
            Enter account details for Piazza service accounts. Leave fields blank to avoid updating them.
            Ensure that these accounts are enrolled in the appropriate Piazzas!
            <form action="/piazza/set_config" method="post">
                <label>
                    Piazza course ID <br />
                    <input name="course_id" type="text"> <br />
                </label>
                <label>
                    Student Username <br />
                    <input name="student_user" type="text"> <br />
                </label>
                <label>
                    Student Password <br />
                    <input name="student_pw" type="password"> <br />
                </label>
                <label>
                    Staff Username <br />
                    <input name="staff_user" type="text"> <br />
                </label>
                <label>
                    Staff Password <br />
                    <input name="staff_pw" type="password"> <br />
                </label>
                <label>
                <input type="submit">
            </form>
        """

    @app.route("/piazza/set_config", methods=["POST"])
    @oauth_secure(app)
    def set_piazza_config():
        with connect_db() as db:
            db(
                """CREATE TABLE IF NOT EXISTS piazza_config (
                    course_id varchar(256),
                    student_user varchar(256),
                    student_pw varchar(256),
                    staff_user varchar(256),
                    staff_pw varchar(256)
                )"""
            )
            ret = db("SELECT * FROM piazza_config").fetchone()
            if ret:
                course_id, student_user, student_pw, staff_user, staff_pw = ret
            else:
                course_id, student_user, student_pw, staff_user, staff_pw = [""] * 5

        course_id = request.form.get("course_id", course_id)
        student_user = request.form.get("student_user", student_user)
        student_pw = request.form.get("student_pw", student_pw)
        staff_user = request.form.get("staff_user", staff_user)
        staff_pw = request.form.get("staff_pw", staff_pw)

        with connect_db() as db:
            # noinspection SqlWithoutWhere
            db("DELETE FROM piazza_config")
            db(
                "INSERT INTO piazza_config VALUES (%s, %s, %s, %s, %s)",
                [course_id, student_user, student_pw, staff_user, staff_pw],
            )
        return "Success!"
