from flask import request, jsonify, redirect
from piazza_api import Piazza

from auth_utils import key_secure, course_oauth_secure
from db import connect_db


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS piazza_config (
                course_id varchar(256),
                test_course_id varchar(256),
                student_user varchar(256),
                student_pw varchar(256),
                staff_user varchar(256),
                staff_pw varchar(256),
                course varchar(128)
            )"""
        )


init_db()


def create_piazza_client(app):
    def piazza_help(course):
        with connect_db() as db:
            ret = db(
                "SELECT student_user, staff_user, course_id, test_course_id FROM piazza_config WHERE course=%s",
                [course],
            ).fetchone()
            student_email, staff_email, course_id, test_course_id = (
                ret if ret else [""] * 4
            )
        return f"""
        <h3> Piazza Service Accounts </h3>
        Student email address: <a href="mailto:{student_email}">{student_email}</a>
        <p>
        Staff email address: <a href="mailto:{staff_email}">{staff_email}</a>
        <p>
        Piazza course: <a href="https://piazza.com/class/{course_id}">https://piazza.com/class/{course_id}</a>
        <p>
        Test Piazza course: <a href="https://piazza.com/class/{test_course_id}">https://piazza.com/class/{test_course_id}</a>
        <p>
        Enroll these accounts on the latest course Piazza.
        <p>
        To configure, go to <a href="/piazza/{course}/config">Piazza Config</a>.
        """

    app.help_info.add(piazza_help)

    @app.route("/piazza/<action>", methods=["POST"])
    @key_secure
    def perform_action(action, course):
        is_staff = request.json["staff"]
        is_test = request.json.get("test", False)
        with connect_db() as db:
            if is_staff:
                user, pw = db(
                    "SELECT staff_user, staff_pw FROM piazza_config WHERE course = (%s)", [course]
                ).fetchone()
            else:
                user, pw = db(
                    "SELECT student_user, student_pw FROM piazza_config WHERE course = (%s)", [course]
                ).fetchone()
            if is_test:
                course_id, = db("SELECT test_course_id FROM piazza_config WHERE course = (%s)", [course]).fetchone()
            else:
                course_id, = db("SELECT course_id FROM piazza_config WHERE course = (%s)", [course]).fetchone()

        p = Piazza()
        p.user_login(user, pw)
        course = p.network(course_id)
        kwargs = dict(request.json)
        del kwargs["staff"]
        del kwargs["client_name"]
        del kwargs["secret"]
        kwargs.pop("test", None)
        try:
            return jsonify(getattr(course, action)(**kwargs))
        except Exception as e:
            return str(e), 400

    @app.route("/piazza/course_id", methods=["POST"])
    @key_secure
    def course_id(course):
        is_test = request.json.get("test", False)
        with connect_db() as db:
            if is_test:
                course_id, = db("SELECT test_course_id FROM piazza_config WHERE course=(%s)", [course]).fetchone()
            else:
                course_id, = db("SELECT course_id FROM piazza_config WHERE course=(%s)", [course]).fetchone()
        return jsonify(course_id)

    @app.route("/piazza/<course>/config", methods=["GET"])
    @course_oauth_secure(app)
    def piazza_config(course):
        return """
            Enter account details for Piazza service accounts. Leave fields blank to avoid updating them.
            Ensure that these accounts are enrolled in the appropriate Piazzas!
            <form action="/piazza/{}/set_config" method="post">
                <label>
                    Piazza course ID <br />
                    <input name="course_id" type="text"> <br />
                </label>
                <label>
                    Test Piazza course ID <br />
                    <input name="test_course_id" type="text"> <br />
                </label>
                <br />
                <label>
                    Student Username <br />
                    <input name="student_user" type="text"> <br />
                </label>
                <label>
                    Student Password <br />
                    <input name="student_pw" type="password"> <br />
                </label>
                <br />
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
        """.format(course)

    @app.route("/piazza/<course>/set_config", methods=["POST"])
    @course_oauth_secure(app)
    def set_piazza_config(course):
        with connect_db() as db:
            ret = db("SELECT * FROM piazza_config WHERE course=(%s)", [course]).fetchone()
            if ret:
                course_id, test_course_id, student_user, student_pw, staff_user, staff_pw, _ = (
                    ret
                )
            else:
                course_id, test_course_id, student_user, student_pw, staff_user, staff_pw = (
                    [""] * 6
                )

        course_id = request.form["course_id"] or course_id
        test_course_id = request.form["test_course_id"] or test_course_id
        student_user = request.form["student_user"] or student_user
        student_pw = request.form["student_pw"] or student_pw
        staff_user = request.form["staff_user"] or staff_user
        staff_pw = request.form["staff_pw"] or staff_pw

        with connect_db() as db:
            db("DELETE FROM piazza_config WHERE course=(%s)", [course])
            db(
                "INSERT INTO piazza_config VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    course_id,
                    test_course_id,
                    student_user,
                    student_pw,
                    staff_user,
                    staff_pw,
                    course,
                ],
            )
        return redirect("/")
