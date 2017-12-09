prepare:
	python3 -m venv env
	env/bin/pip install -Ur requirements.txt

serve:
	FLASK_APP=server.py env/bin/flask run
