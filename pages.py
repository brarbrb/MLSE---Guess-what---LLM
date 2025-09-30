from pathlib import Path

from flask import Blueprint, render_template, redirect, url_for, send_from_directory

pages = Blueprint('pages', __name__)


@pages.route('/', methods=['GET'])
def index():
    return render_template('menu.html')


@pages.route('/menu', methods=['GET'])
def menu():
    return redirect(url_for('pages.index'))


@pages.route('/room/<int:room_id>', methods=['GET'])
def room(room_id: int):
    return render_template('room.html', room=room_id)


@pages.route('/favicon.ico', methods=['GET'])
def favicon():
    directory = Path(pages.root_path).parent.parent / 'frontend'
    return send_from_directory(directory, 'static/images/favicon.ico', mimetype='image/vnd.microsoft.icon')
