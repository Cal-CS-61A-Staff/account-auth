import string
from random import SystemRandom

from flask import request

from db import connect_db
from auth_utils import oauth_secure, get_name


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS auth_keys (
                client_name varchar(128), 
                auth_key varchar(128),
                creator varchar(128),
                unused BOOLEAN
             )"""
        )


init_db()


def gen_key(length=64):
    return "".join(
        SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(length)
    )


class Data:
    def __init__(self):
        self.callbacks = []

    def add(self, callback):
        self.callbacks.append(callback)

    def render(self):
        return "<p>".join(callback() for callback in self.callbacks)


def create_management_client(app):
    app.help_info = Data()

    def general_help():
        return """
            <title>61A Auth</title>
            <link rel="icon" href="https://cs61a.org/assets/images/favicon.ico">
            <h2> 61A Auth </h2>
            Go to <a href="https://go.cs61a.org/auth-help">go/auth-help</a> to see detailed usage / deployment instructions.
        """

    def client_data():
        with connect_db() as db:
            ret = db("SELECT client_name, creator, unused FROM auth_keys").fetchall()
        client_names = [
            '{}, created by {} {} (<a href="/api/revoke_key?client_name={}">Remove</a>)'.format(
                client_name, creator, "(unused)" if unused else "", client_name,
            )
            for client_name, creator, unused in ret
        ]
        create_client = """
            Create new client and obtain secret key:
            <form action="/api/request_key" method="get">
                <input name="client_name" type="text" placeholder="client_name">
                <input type="submit">
            </form>
        """
        return "<h3>Clients</h3>" + create_client + "<p>".join(client_names)

    app.help_info.add(general_help)
    app.help_info.add(client_data)

    @app.route("/")
    @oauth_secure(app)
    def index():
        return app.help_info.render()

    @app.route("/api/request_key", methods=["GET", "POST"])
    @oauth_secure(app)
    def create_key():
        name = request.args["client_name"]
        key = gen_key()
        with connect_db() as db:
            ret = db(
                "SELECT * FROM auth_keys WHERE client_name = (%s)", [name]
            ).fetchone()
            if ret:
                return "client_name already in use", 409
            db("INSERT INTO auth_keys VALUES (%s, %s, %s, TRUE)", [name, key, get_name(app.remote)])
        return key

    @app.route("/api/revoke_key", methods=["GET", "POST"])
    @oauth_secure(app)
    def revoke_key():
        name = request.args["client_name"]
        with connect_db() as db:
            db("DELETE FROM auth_keys WHERE client_name = (%s)", [name])
        return "Key {} revoked".format(name)

    @app.route("/api/revoke_all_unused_keys", methods=["GET", "POST"])
    @oauth_secure(app)
    def revoke_all_unused_keys():
        with connect_db() as db:
            db("DELETE FROM auth_keys WHERE unused = TRUE")
        return "All unused keys revoked."

    @app.route("/api/DANGEROUS_revoke_all_keys", methods=["GET"])
    @oauth_secure(app)
    def revoke_all_keys():
        with connect_db() as db:
            db("DROP TABLE auth_keys")
            init_db()
        return "ALL keys revoked. Any tools depending on 61A Auth will no longer work."
