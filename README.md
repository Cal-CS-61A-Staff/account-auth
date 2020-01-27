# 61A Auth

This tool allows applications to access Google Drive (and eventually Piazza) by wrapping the two APIs in a much simpler OKPy-based interface. 

## Quickstart

To start, visit [auth.apps.cs61a.org](https://auth.apps.cs61a.org) and register a client with a unique `client_name`. Keep track of the `secret` returned after you register a client - you can't generate it again!

The `secret` lets applications access any Google Document or Sheet that is shared with the service account. The service account email address can be seen at  [auth.apps.cs61a.org](https://auth.apps.cs61a.org). **IMPORTANT: If the `secret` is compromised, _IMMEDIATELY_ go to [auth.apps.cs61a.org](https://auth.apps.cs61a.org) and recreate the client with a new `secret`**, as anyone with the `secret` can access any document shared with the service account.

## Basic Usage

To read a Google Document, ensure that the service account has access to it, either by making the document visible to "anyone with the link" or by sharing it with the service account directly. Then, you can read the Google Document by making a POST request to `auth.apps.cs61a.org/google/read_document` with the document `url` as a JSON-encoded POST parameter, along with the `client_name` and `secret` For example, in Python, you can do
```python
import requests

text = requests.post("https://auth.apps.cs61a.org/google/read_document", json={
    "url": "https://docs.google.com/document/d/10xo4ofWCnYbmmNBGDGQqVfpOZVo/edit",
    "client_name": "my-client",
    "secret": "my-secret"
}).json()
```
The JSON-encoded body of the response will be the plain text content of that document.

To read a Google Sheet (e.g. to use one to configure an application), make an analogous POST request to `https://auth.apps.cs61a.org/google/read_spreadsheet` with the same parameters before, except also include the parameter `sheet_name` to indicate which sheet of the spreadsheet you want to export. For instance, you can do
```python
import requests

data = requests.post("https://auth.apps.cs61a.org/google/read_document", json={
    "url": "https://docs.google.com/spreadsheets/d/1sUeanmzo_Kj1HaXM2v0/edit",
    "sheet_name": "Sheet5"
    "client_name": "my-client",
    "secret": "my-secret",
}).json()
```
The body of the response will be a `List[List[String]]`, with the outer list containing each row until the last non-empty row, and the inner list containing each cell in its corresponding row until the last non-empty cell. As before, it will be JSON-encoded.

## Advanced Usage
To programmatically create a client, make a POST request to `/api/request_key` with an OKPy cookie corresponding to an account with staff access to the okpy course `cal/cs61a/CURR_SEMESTER`. You can generate such a cookie by running `python3 ok --get-token` and storing it in the cookie `dev_token`. For the remainder of this section, all POST requests will require such a cookie to be in place.

To revoke a key corresponding to a particular client, make a POST request to `/api/revoke_key?client_name=<CLIENT_NAME>` with the `client_name` parameter set to the name of the desired client whose key is being revoked.

To revoke all keys that have never been used to handle a request, make a POST request to `/api/revoke_all_unused_keys`. You can also visit this link in the browser directly while signed into OKPy to perform the same action.

To revoke *ALL* keys that have been issued, even those currently in use, make a POST request to `/api/DANGEROUS_revoke_all_keys`. In production, it should be very rare that this needs to be done - consider revoking individual keys by visiting the website or invoking the `revoke_key` API on individual clients.

## Deployment Instructions
To quickly deploy an update, run `make deploy`. When deploying for the first time, you must first create a MySQL database linked to the app by running `dokku mysql:create auth auth`, before deploying. After deploying, you must visit `[auth.apps.cs61a.org/google/config](https://auth.apps.cs61a.org/google/config)` and upload a JSON corresponding to the Google service account, in order for the app to start working.

## Obtaining a Google Service Account
Go to [console.cloud.google.com](https://console.cloud.google.com), create a project, then go to `IAM & admin -> Service accounts` and create a new account. You do not need to give this account a role, but you must download a file containing a JSON private key and upload it to the 61A Auth service.