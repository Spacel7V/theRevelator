from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, abort
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}
MAX_CONTENT_LENGTH = 150 * 1024 * 1024  # 150 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

videos = []

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    ip = db.Column(db.String(45), nullable=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def index():
    if session.get('logged_in'):
        videos = Video.query.all()
        return render_template('index.html', videos=videos)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'Martin-Victor@47#':
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'):
        abort(403)

    if 'video' not in request.files:
        return 'No file part', 400
    file = request.files['video']
    description = request.form.get('description')
    if file.filename == '' or not allowed_file(file.filename):
        return 'Invalid file', 400

    filename = secure_filename(str(uuid.uuid4()) + '_' + file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    uploader_ip = request.remote_addr
    new_video = Video(filename=filename, description=description, ip=uploader_ip)
    db.session.add(new_video)
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/video/<filename>')
def view_video(filename):
    video = Video.query.filter_by(filename=filename).first()
    if not video:
        abort(404)
    return render_template('video.html', video=video)


@app.route('/manifest.json')
def manifest_json():
    return send_from_directory('static', 'manifest.json')


@app.route('/service-worker.js')
def sw():
    return send_from_directory('static', 'service-worker.js')

@app.route('/delete/<filename>', methods=['POST'])
def delete_video(filename):
    if not session.get('logged_in'):
        abort(403)
    video = Video.query.filter_by(filename=filename).first()
    if not video:
        abort(404)
    # Supprimer le fichier du disque
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    # Supprimer de la base de données
    db.session.delete(video)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)