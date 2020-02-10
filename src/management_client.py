import re
import string
from random import SystemRandom

from flask import request, redirect, jsonify

from db import connect_db
from auth_utils import oauth_secure, get_name, admin_oauth_secure, course_oauth_secure, MASTER_COURSE, is_staff, \
    is_logged_in


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS auth_keys (
                client_name varchar(128), 
                auth_key varchar(128),
                creator varchar(128),
                course varchar(128),
                service varchar(128),
                unused BOOLEAN
             )"""
        )
        db(
            """CREATE TABLE IF NOT EXISTS courses (
                course varchar(128),
                endpoint varchar(128)
            )"""
        )
        ret = db("SELECT * FROM courses WHERE course=(%s)", [MASTER_COURSE]).fetchone()
        if not ret:
            db("INSERT INTO courses VALUES (%s, %s)", ["cs61a", "cal/cs61a/sp20"])


init_db()


def gen_key(length=64):
    return "".join(
        SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(length)
    )


def prettify(course_code):
    m = re.match(r"([a-z]+)([0-9]+[a-z]?)", course_code)
    return m and (m.group(1) + " " + m.group(2)).upper()


class Data:
    def __init__(self):
        self.callbacks = []

    def add(self, callback):
        self.callbacks.append(callback)

    def render(self, *args):
        return "<p>".join(callback(*args) for callback in self.callbacks)


def create_management_client(app):
    app.general_info = Data()
    app.help_info = Data()

    def general_help():
        return """
            <title>61A Auth</title>
            <link rel="icon" href="https://cs61a.org/assets/images/favicon.ico">
            <h1> 61A Auth </h1>
            Go to <a href="https://go.cs61a.org/auth-help">go/auth-help</a> to see detailed usage / deployment instructions.
        """

    def add_course():
        if not is_logged_in(app, MASTER_COURSE):
            return ""
        with connect_db() as db:
            courses = db("SELECT course, endpoint FROM courses").fetchall()
        courses = [
            '{} ({}), at endpoint {} (<a href="/api/remove_course?course={}">Remove</a>)'.format(
                prettify(course), course, endpoint, course
            )
            for course, endpoint in courses
        ]
        return """
            <h2>Admin</h2>
            Activate Auth for a new course (method only available to 61A staff):
            <form action="/api/add_course" method="post">
                <input name="course" type="text" placeholder="course name">
                <input name="endpoint" type="text" placeholder="OKPy endpoint">
                <input type="submit">
            </form>
        """ + "<p>".join(
            courses
        )

    app.general_info.add(general_help)
    app.general_info.add(add_course)

    def client_data(course):
        with connect_db() as db:
            ret = db(
                "SELECT client_name, creator, unused FROM auth_keys WHERE course=(%s)",
                [course],
            ).fetchall()
        client_names = [
            '{}, created by {} {} (<a href="/api/{}/revoke_key?client_name={}">Remove</a>)'.format(
                client_name, creator, "(unused)" if unused else "", course, client_name
            )
            for client_name, creator, unused in ret
        ]
        create_client = """
            Create new client and obtain secret key:
            <form action="/api/{}/request_key" method="get">
                <input name="client_name" type="text" placeholder="client_name">
                <input type="submit">
            </form>
        """.format(course)
        return "<h3>Clients</h3>" + create_client + "<p>".join(client_names)

    def course_config(course):
        with connect_db() as db:
            endpoint = db(
                "SELECT endpoint FROM courses WHERE course=(%s)", [course]
            ).fetchone()[0]
            return """
                <h3>Config</h3>
                <p>
                Current endpoint: {}
                </p>
                Set new endpoint:
                <form action="/api/{}/set_endpoint" method="post">
                    <input name="endpoint" type="text" placeholder="OKPy endpoint">
                    <input type="submit">
                </form>
            """.format(
                endpoint, course
            )

    app.help_info.add(lambda course: "<h2>{}</h2>".format(prettify(course)))
    app.help_info.add(course_config)
    app.help_info.add(client_data)

    @app.route("/")
    @oauth_secure(app)
    def index():
        out = [app.general_info.render()]
        with connect_db() as db:
            for course, endpoint in db("SELECT course, endpoint FROM courses").fetchall():
                if is_staff(app.remote, endpoint):
                    out.append(app.help_info.render(course))
        return "".join(out)

    @app.route("/api/add_course", methods=["POST"])
    @admin_oauth_secure(app)
    def add_course():
        course = request.form["course"]
        endpoint = request.form["endpoint"]
        if not prettify(course):
            return "Course code not formatted correctly. It should be lowercase with no spaces.", 400
        with connect_db() as db:
            ret = db("SELECT * FROM courses WHERE course = (%s)", course).fetchone()
            if ret:
                return "A course already exists with the same name.", 403
            db("INSERT INTO courses VALUES (%s, %s)", [course, endpoint])
        return redirect("/")

    @app.route("/api/remove_course", methods=["GET"])
    @admin_oauth_secure(app)
    def remove_course():
        course = request.args["course"]
        with connect_db() as db:
            db("DELETE FROM courses WHERE course = (%s)", [course])
        return redirect("/")

    @app.route("/api/<course>/get_endpoint", methods=["POST"])
    def get_endpoint(course):
        # note: deliberately not secured, not sensitive data
        with connect_db() as db:
            endpoint = db("SELECT endpoint FROM courses WHERE course = (%s)", [course]).fetchone()
        if endpoint:
            return jsonify(endpoint[0])
        else:
            return jsonify(None)

    @app.route("/api/<course>/set_endpoint", methods=["POST"])
    @course_oauth_secure(app)
    def set_endpoint(course):
        endpoint = request.form["endpoint"]
        with connect_db() as db:
            db("UPDATE courses SET endpoint = (%s) WHERE course = (%s)", [endpoint, course])
        return redirect("/")

    @app.route("/api/<course>/request_key", methods=["GET", "POST"])
    @course_oauth_secure(app)
    def create_key(course):
        name = request.args["client_name"]
        key = gen_key()
        with connect_db() as db:
            ret = db(
                "SELECT * FROM auth_keys WHERE client_name = (%s)", [name]
            ).fetchone()
            if ret:
                return "client_name already in use", 409
            db(
                "INSERT INTO auth_keys VALUES (%s, %s, %s, %s, %s, %s)",
                [name, key, get_name(app.remote), course, "all", True],
            )
        return key

    @app.route("/api/<course>/revoke_key", methods=["GET", "POST"])
    @course_oauth_secure(app)
    def revoke_key(course):
        name = request.args["client_name"]
        with connect_db() as db:
            db("DELETE FROM auth_keys WHERE client_name = (%s) and course = (%s)", [name, course])
        return redirect("/")

    @app.route("/api/<course>/revoke_all_unused_keys", methods=["GET", "POST"])
    @course_oauth_secure(app)
    def revoke_all_unused_keys(course):
        with connect_db() as db:
            db("DELETE FROM auth_keys WHERE unused = TRUE and course = (%s)", [course])
        return "All unused keys revoked."

    @app.route("/api/DANGEROUS_revoke_all_keys", methods=["POST"])
    @admin_oauth_secure(app)
    def revoke_all_keys():
        with connect_db() as db:
            db("DROP TABLE auth_keys")
            init_db()
        return "ALL keys revoked. Any tools depending on 61A Auth will no longer work."
