import os, time, shutil, random, string
import requests
import threading
from flask import Flask, request, redirect, url_for, make_response, jsonify, abort
from flask import render_template
from werkzeug.utils import secure_filename
from classify_portrait import classify_portrait
from flask import copy_current_request_context

UPLOAD_FOLDER = './portraits'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/', methods=['GET'])
def hello():
    time.sleep(5)
    json = {
        "upload-picture": "/classification/portrait/upload",
        "url": "/classification/portrait/url"
    }
    return jsonify(json)

@app.route('/classification/portrait/upload', methods=['POST'])
def classify_upload():
    # check if the post request has the file part
    print(request.form)
    print(request.files)
    if 'file' not in request.files:
        return make_response(jsonify({'error': 'Files attribute not in request.'}), 404)
    file = request.files['file']
    # if the user doesn't select a file, the browser
    # submits an empty  filename
    if file.filename == '':
        return make_response(jsonify({'error': 'No file selected.'}), 404)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        predictions = classify_portrait(filepath)
        return jsonify(predictions)


@app.route('/classification/portrait/url', methods=['POST'])
def web_classify_url():
    url = request.form.get('url')
    if not url:
        return make_response(jsonify({'error': 'No URL provided.'}), 404)
    try:
        response = requests.get(url, stream=True)
    except:
        return make_response(jsonify({'error': 'URL not valid.'}), 404)
    # random id: https://stackoverflow.com/a/30779367
    filename = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename + ".jpg")
    with open(img_path, 'w+b') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response
    predictions = classify_portrait(img_path)
    return jsonify(predictions)


@app.route('/slack/classification/portrait/url', methods=['POST'])
def slack_classify_url():
    print(request.form)
    print(request.form.get('text'))
    url = request.form.get('text')
    if not url:
        return 'No URL provided.'
    # random id: https://stackoverflow.com/a/30779367
    @copy_current_request_context
    def slack_classify_portrait():
        url = request.form.get('text')
        response_url = request.form.get('response_url')
        try:
            req_response = requests.get(url, stream=True)
        except:
            response_json = {
                "text": "URL not valid."
            }
            requests.post(response_url, json=response_json)
        filename = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename + ".jpg")
        with open(img_path, 'w+b') as out_file:
            shutil.copyfileobj(req_response.raw, out_file)
        del req_response
        predictions = classify_portrait(img_path)
        response_json = {
            "text": "This portrait is clearly of a {}, {} Person".format(predictions["gender"], predictions["ethnicity"])
        }
        requests.post(response_url, json=response_json)
    t = threading.Thread(target=slack_classify_portrait)
    t.start()
    return "Cool, now give me a second. I'll get back to you."



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
