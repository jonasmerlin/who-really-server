import os
import random
import shutil
import string
import threading
import time

import git
import requests
from flask import (Flask, request, redirect, url_for, make_response, jsonify,
                abort, render_template, copy_current_request_context)
from werkzeug.utils import secure_filename

from classify_portrait import classify_portrait
from server_exceptions import URLError

def get_git_root(path):
    """Returns the root of the containing git repo.

    Source: https://stackoverflow.com/a/41920796
    """
    git_repo = git.Repo(path, search_parent_directories=True)
    git_root = git_repo.git.rev_parse("--show-toplevel")
    print(git_root)
    return git_root


UPLOAD_FOLDER = './portraits'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create portraits folder on first run.
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    """Checks if the provided file is in one of the allowed formats."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def make_file_name(length):
    """Returns a random alphanumeric string of lenght length.

    This ID is not guaranteed to be unique, but it is sufficiently probable
    for our purposes.
    Source: https://stackoverflow.com/a/30779367
    """
    name = ''.join(
        random.choice(
            string.ascii_letters + string.digits
        ) for _ in range(length)
    )
    return name


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


def download_img(url):
    """Downloads an image from a url.

    Returns either the path of the downloaded image or raises an URLError
    specifying why the error was raised in its message attriute.
    """
    if not url:
        raise URLError('No URL provided.')
    file_ext = url.split(".")[-1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise URLError('File type is not allowed.')
    try:
        req_response = requests.get(url, stream=True)
    except RequestException:
        raise URLError('URL does not respond or is not valid.')
    filename = make_file_name(16)
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename + file_ext)
    with open(img_path, 'w+b') as out_file:
        shutil.copyfileobj(req_response.raw, out_file)
    del req_response
    return img_path


@app.route('/', methods=['GET'])
def hello():
    """Returns a JSON object listing all API routes."""
    json = {
        "upload-picture": "/classification/portrait/upload",
        "url": "/classification/portrait/url"
    }
    return jsonify(json)


@app.route('/classification/portrait/upload', methods=['POST'])
def classify_upload():
    """Classify a file uploaded by the user.

    Returns a JSON object containing key-value pairs of the name and result
    of each classifier.
    """
    # Check if the post request has a file attribute.
    if 'file' not in request.files:
        return make_response(jsonify({
            'error': 'Files attribute not in request.'
        }), 404)
    file = request.files['file']
    # If the user doesn't select a file, the browser submits an empty filename.
    if file.filename == '':
        return make_response(jsonify({
            'error': 'No file selected.'
            }), 404)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        predictions = classify_portrait(filepath)
        return jsonify(predictions)


@app.route('/classification/portrait/url', methods=['POST'])
def web_classify_url():
    """Classify a the file behind a user-provided url.

    Expects a url field to be present in the request form data.

    Returns a JSON object containing key-value pairs of the name and result
    of each classifier.
    """
    url = request.form.get('url')
    try:
        img_path = download_img(url)
    except URLError as e:
        return make_response(jsonify({'error': e.message}), 404)
    predictions = classify_portrait(img_path)
    return jsonify(predictions)


@app.route('/slack/classification/portrait/url', methods=['POST'])
def slack_classify_url():
    """URL classification route specifically for Slack slash-command."""

    # Slack expects an answer in less than 3000ms
    # Since both the request for the image as well as the classification
    # run longer than that, we need to post our response later.
    # That's why we copy the current request context to a function that does
    # exaxtly that.
    @copy_current_request_context
    def slack_classify_portrait():
        url = request.form.get('text')
        slack_response_url = request.form.get('response_url')
        try:
            img_path = download_img(url)
        except URLError as e:
            response_json = {
                "text": e.message
            }
            requests.post(slack_response_url, json=response_json)
        predictions = classify_portrait(img_path)
        response_json = {
            "text": "This portrait is clearly of a {}, {} Person"
            .format(predictions["gender"], predictions["ethnicity"])
        }
        requests.post(slack_response_url, json=response_json)

    # We call the function in a separate thread, so we can let the user know
    # immidiately that we are working on his or her request.
    t = threading.Thread(target=slack_classify_portrait)
    t.start()
    return "Cool, now give me a second. I'll get back to you."


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
