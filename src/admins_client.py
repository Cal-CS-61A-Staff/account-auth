from flask import redirect, request, url_for, jsonify

from auth_utils import course_oauth_secure, get_name
from db import connect_db


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS course_admins (
                email varchar(128), 
                name varchar(128), 
                course varchar(128),
                creator varchar(128)
             )"""
        )


init_db()


def create_admins_client(app):
    def client_data(course):
        with connect_db() as db:
            ret = db(
                "SELECT email, name, course, creator FROM course_admins WHERE course=(%s)",
                [course],
            ).fetchall()
        admin_names = [
            f'{name} (<a href="mailto:{email}">{email}</a>), added by {creator} '
            f'(<a href="{url_for("remove_admin", course=course, email=email)}">Remove</a>)'
            for email, name, course, creator in ret
        ]
        create_client = f"""
            Add new course administrator:
            <form action="{url_for("add_admin", course=course)}" method="post">
                <input name="email" type="email" placeholder="Email address">
                <input type="submit">
            </form>
        """
        return "<h3>Admins</h3>" + create_client + "<p>".join(admin_names)

    app.help_info.add(client_data)

    @course_oauth_secure(app)
    @app.route("/admins/<course>/add_admin", methods=["POST"])
    def add_admin(course):
        email = request.form["email"]
        with connect_db() as db:
            check = db("SELECT * FROM course_admins WHERE email=(%s) AND course=(%s)", [email, course]).fetchone()
        if check:
            return "User is already an admin", 409
        with connect_db() as db:
            db("INSERT INTO course_admins VALUES (%s, %s, %s, %s)", [email, "Unknown", course, get_name(app.remote)])
        return redirect(url_for("index"))

    @course_oauth_secure(app)
    @app.route("/admins/<course>/remove_admin", methods=["GET"])
    def remove_admin(course):
        email = request.args["email"]
        with connect_db() as db:
            db("DELETE FROM course_admins WHERE email=(%s) AND course=(%s)", [email, course])
        return redirect(url_for("index"))

    @app.route("/admins/<course>/is_admin", methods=["POST"])
    def is_admin(course):
        # note: deliberately not secured, not sensitive data
        email = request.json["email"]
        with connect_db() as db:
            return jsonify(bool(db("SELECT * FROM course_admins WHERE email=(%s) AND course=(%s)", [email, course]).fetchone()))
