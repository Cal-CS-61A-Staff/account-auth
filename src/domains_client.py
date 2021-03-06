from flask import jsonify, redirect, request, url_for

from auth_utils import course_oauth_secure
from db import connect_db
from html_utils import make_row


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS domains_config (
                domain varchar(128), 
                course varchar(128)
             )"""
        )


init_db()


def create_domains_client(app):
    def domains_help(course):
        with connect_db() as db:
            ret = db(
                "SELECT domain FROM domains_config WHERE course=(%s)",
                [course],
            ).fetchall()
        client_names = [
            make_row(domain, url_for("remove_domain", domain=domain, course=course))
            for domain, in ret
        ]
        register_domain = f"""
            Register new domain:
            <form action="/domains/{course}/register_domain" method="post">
                <input name="domain_name" type="text" placeholder="seating.cs61a.org">
                <input type="submit">
            </form>
        """
        return "<h3>Domains</h3>" + register_domain + "<p>".join(client_names)

    app.help_info.add(domains_help)

    @app.route("/domains/<course>/register_domain", methods=["POST"])
    @course_oauth_secure(app)
    def register_domain(course):
        domain_name = request.form["domain_name"]
        with connect_db() as db:
            ret = db(
                "SELECT * FROM domains_config WHERE domain = (%s)", [domain_name]
            ).fetchone()
            if ret:
                return "domain already registered", 409
            db(
                "INSERT INTO domains_config VALUES (%s, %s)",
                [domain_name, course],
            )
        return redirect("/")

    @app.route("/domains/<course>/remove_domain", methods=["POST"])
    @course_oauth_secure(app)
    def remove_domain(course):
        domain = request.args["domain"]
        with connect_db() as db:
            db(
                "DELETE FROM domains_config WHERE domain = (%s) AND course = (%s)",
                [domain, course],
            )
        return redirect("/")

    @app.route("/domains/get_course", methods=["POST"])
    def get_course():
        # note: deliberately not secured, not sensitive data
        domain = request.json["domain"]
        with connect_db() as db:
            [course] = db("SELECT course FROM domains_config WHERE domain = (%s)", [domain]).fetchone()
        return jsonify(course)
