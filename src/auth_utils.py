from functools import wraps

from flask import session, request, url_for, redirect, abort

from db import connect_db

AUTHORIZED_ROLES = ["staff", "instructor"]
ENDPOINT = "cal/cs61a/sp20"


def is_staff(remote):
    try:
        token = session.get("dev_token") or request.cookies.get("dev_token")
        if not token:
            return False
        ret = remote.get("user")
        for course in ret.data["data"]["participations"]:
            if course["role"] not in AUTHORIZED_ROLES:
                continue
            if course["course"]["offering"] != ENDPOINT:
                continue
            return True
        return False
    except Exception as e:
        # fail safe!
        print(e)
        return False


def get_name(remote):
    return remote.get("user").data["data"]["name"]


def oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            if not is_staff(app.remote):
                return redirect(url_for("login"))
            return route(*args, **kwargs)

        return wrapped

    return decorator


def key_secure(route):
    @wraps(route)
    def wrapped(*args, **kwargs):
        client_name = request.json["client_name"]
        secret = request.json["secret"]
        with connect_db() as db:
            ret = db(
                "SELECT * FROM auth_keys WHERE client_name=(%s) AND auth_key = (%s)",
                [client_name, secret],
            ).fetchone()
            if not ret:
                abort(401)
            db(
                "UPDATE auth_keys SET unused = FALSE WHERE client_name=(%s)",
                [client_name],
            )
        return route(*args, **kwargs)

    return wrapped
