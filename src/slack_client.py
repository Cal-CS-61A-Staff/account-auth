from flask import request, jsonify, redirect

from auth_utils import key_secure, course_oauth_secure
from db import connect_db


def init_db():
    with connect_db() as db:
        db(
            """CREATE TABLE IF NOT EXISTS slack_config (
                course varchar(128),
                workspace varchar(128)
            )"""
        )


init_db()


def create_slack_client(app):
    def slack_help(course):
        with connect_db() as db:
            workspace = db(
                "SELECT workspace FROM slack_config WHERE course=(%s)", [course]
            ).fetchone()
            workspace = workspace[0] if workspace else ""
        return f"""
        <h3> Slack Configuration </h3>
        Current workspace: <a href="https://{workspace}.slack.com">{workspace}.slack.com</a>
        <p>
        <p>
        To configure, go to <a href="/slack/{course}/config">Slack Config</a>.
        """

    app.help_info.add(slack_help)

    @app.route("/slack/workspace_name", methods=["POST"])
    @key_secure
    def workspace_name(course):
        with connect_db() as db:
            workspace, = db(
                "SELECT workspace FROM slack_config WHERE course=(%s)", [course]
            ).fetchone()
        return jsonify(workspace)

    @app.route("/slack/<course>/config", methods=["GET"])
    @course_oauth_secure(app)
    def slack_config(course):
        return """
            Enter Slack workspace url.
            <form action="/slack/{}/set_config" method="post">
                <label>
                    Slack Workspace <br />
                    <input name="workspace" type="text" placeholder="cs61a.slack.com"> <br />
                </label>
                <label>
                <input type="submit">
            </form>
        """.format(
            course
        )

    @app.route("/slack/<course>/set_config", methods=["POST"])
    @course_oauth_secure(app)
    def set_slack_config(course):
        workspace = request.form["workspace"].split(".")[0]

        with connect_db() as db:
            db("DELETE FROM slack_config WHERE course=(%s)", [course])
            db("INSERT INTO slack_config VALUES (%s, %s)", [course, workspace])

        return redirect("/")
