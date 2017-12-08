import os, time, shutil, random, string
import requests
from flask import Flask, request, redirect, url_for, make_response, jsonify, abort
from flask import render_template
from werkzeug.utils import secure_filename
from classify_portrait import classify_portrait

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
def classify_url():
    # url = request.args.get('url', '')
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
def classify_url():
    print(request)
    return "Hey, I got your message and uh ... I don't want to be friends anymore. Sorry!"


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
