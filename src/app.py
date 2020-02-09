from flask import Flask

from google_client import create_google_client
from management_client import create_management_client
from oauth_client import create_oauth_client
from piazza_client import create_piazza_client

app = Flask(__name__)
create_oauth_client(app)
create_management_client(app)
create_google_client(app)
create_piazza_client(app)


if __name__ == '__main__':
    app.run(debug=True)
