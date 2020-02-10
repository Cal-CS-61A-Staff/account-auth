from functools import wraps

from flask import session, request, url_for, redirect, abort

from db import connect_db

AUTHORIZED_ROLES = ["staff", "instructor", "grader"]


def is_staff(remote, endpoint):
    try:
        token = session.get("dev_token") or request.cookies.get("dev_token")
        if not token:
            return False
        ret = remote.get("user")
        for course in ret.data["data"]["participations"]:
            if course["role"] not in AUTHORIZED_ROLES:
                continue
            if course["course"]["offering"] != endpoint and endpoint is not None:
                continue
            return True
        return False
    except Exception as e:
        # fail safe!
        print(e)
        return False


def get_name(remote):
    return remote.get("user").data["data"]["name"]


def is_logged_in(app, course=None):
    if course:
        with connect_db() as db:
            endpoint = db("SELECT endpoint FROM courses WHERE course=(%s)", [course]).fetchone()[0]
    else:
        endpoint = None
    return is_staff(app.remote, endpoint)


def admin_oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            assert "course" not in kwargs
            if not is_logged_in(app, MASTER_COURSE):
                return redirect(url_for("login"))
            return route(*args, **kwargs)

        return wrapped

    return decorator


def course_oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            if not is_logged_in(app, kwargs["course"]):
                return redirect(url_for("login"))
            return route(*args, **kwargs)

        return wrapped

    return decorator


def oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            if not is_staff(app.remote, None):
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
                "SELECT course FROM auth_keys WHERE client_name=(%s) AND auth_key = (%s)",
                [client_name, secret],
            ).fetchone()
            if not ret:
                abort(401)
            db(
                "UPDATE auth_keys SET unused = FALSE WHERE client_name=(%s)",
                [client_name],
            )
        return route(*args, **kwargs, course=ret[0])

    return wrapped


MASTER_COURSE = "cs61a"
