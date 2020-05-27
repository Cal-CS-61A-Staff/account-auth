from functools import wraps

from flask import session, request, url_for, redirect, abort, g

from db import connect_db

AUTHORIZED_ROLES = ["staff", "instructor", "grader"]


def get_user(remote):
    g.user_data = g.get("user_data") or remote.get("user")
    return g.user_data


def is_staff(remote, course):
    try:
        token = session.get("dev_token") or request.cookies.get("dev_token")
        if not token:
            return False

        email = get_user(remote).data["data"]["email"]
        with connect_db() as db:
            if course:
                admins = db("SELECT email FROM course_admins WHERE course=(%s)", [course]).fetchall()
                admins = set(x[0] for x in admins)
                if admins:
                    if email in admins:
                        db("UPDATE course_admins SET name=(%s) WHERE email=(%s)", [get_name(remote), email])
                        return True
                    else:
                        return False

        # otherwise, let anyone on staff access
        with connect_db() as db:
            if course is not None:
                [endpoint] = db("SELECT endpoint FROM courses WHERE course=(%s)", [course])
            else:
                endpoint = None
        for participation in get_user(remote).data["data"]["participations"]:
            if participation["role"] not in AUTHORIZED_ROLES:
                continue
            if participation["course"]["offering"] != endpoint and endpoint is not None:
                continue
            return True
        return False
    except Exception as e:
        # fail safe!
        print(e)
        return False


def get_name(remote):
    return get_user(remote).data["data"]["name"]


def get_email(remote):
    return get_user(remote).data["data"]["email"]


def admin_oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            assert "course" not in kwargs
            if not is_staff(app.remote, MASTER_COURSE):
                return redirect(url_for("login"))
            return route(*args, **kwargs)

        return wrapped

    return decorator


def course_oauth_secure(app):
    def decorator(route):
        @wraps(route)
        def wrapped(*args, **kwargs):
            if not is_staff(app.remote, kwargs["course"]):
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
            ret_regular = db(
                "SELECT course FROM auth_keys WHERE client_name=(%s) AND auth_key = (%s)",
                [client_name, secret],
            ).fetchone()
            ret_super = db(
                "SELECT client_name FROM super_auth_keys WHERE client_name=(%s) AND auth_key = (%s)",
                [client_name, secret],
            ).fetchone()
            if ret_regular:
                db(
                    "UPDATE auth_keys SET unused = FALSE WHERE client_name=(%s)",
                    [client_name],
                )
                course = ret_regular[0]
            elif ret_super:
                db(
                    "UPDATE super_auth_keys SET unused = FALSE WHERE client_name=(%s)",
                    [client_name],
                )
                course = request.json["course"]
            else:
                abort(401)
        return route(*args, **kwargs, course=course)

    return wrapped


MASTER_COURSE = "cs61a"
