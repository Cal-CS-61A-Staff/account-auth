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
            f'{domain} (<a href="/domains/{course}/remove_domain?domain={domain}">Remove</a>)'
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

    @app.route("/domains/<course>/remove_domain", methods=["GET", "POST"])
    @course_oauth_secure(app)
    def remove_domain(course):
        domain = request.args["domain"]
        with connect_db() as db:
            db(
                "DELETE FROM domains_config WHERE domain = (%s) AND course = (%s)",
                [domain, course],
            )
        return redirect("/")
