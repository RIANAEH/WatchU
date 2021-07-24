from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, g, url_for

from watchu_db.models import Professor, TestRoom, Student, Log
from watchu_db import db
import secrets

from watchu_db.views import auth_views

bp = Blueprint('test_room', __name__, url_prefix='/test_room')

@bp.route('/')
@bp.route('/menu')
@auth_views.login_required
def menu():
    return render_template('test_room/menu.html')

@bp.route('/make', methods=["GET"])
@auth_views.login_required
def make():
    test_room_id = secrets.token_urlsafe(11)
    print(test_room_id)
    return render_template('test_room/make.html', test_room_id=test_room_id)

@bp.route('/ajax', methods=['GET', 'POST'])
def ajax():
    test_room_id = request.form['test_room_id']
    professor_id = request.form['professor_id']
    block_list = request.form['block_list']

    date = request.form['date'].split('-')
    start = request.form['start_time'].split(':')
    end = request.form['end_time'].split(':')
    start_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(start[0]), int(start[1]))
    end_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(end[0]), int(end[1]))
    # db에 TestRoom, Student 객체 생성 및 저장
    test_room = TestRoom(
        id=test_room_id,
        professor=Professor.query.get(professor_id),
        block_list=block_list,
        start_date=start_date, end_date=end_date)
    db.session.add(test_room)
    length = request.form['length']
    for i in range(int(length)):
        image = request.files[str(i)]
        id = image.filename[:8]
        image_data = image.read()
        student = Student(id=id, test_room_id=test_room_id, image=image_data)
        db.session.add(student)
    db.session.commit()
    return "ajax"

@bp.route('/edit_list', methods=["GET"])
@auth_views.login_required
def edit_list():
    professor = Professor.query.get(g.user.id)
    test_room_list = []
    for t in professor.test_room_set:
        test_room_list.append(t.id)
    return render_template('test_room/edit_list.html', test_room_list=test_room_list)

@bp.route('/edit/<string:test_room_id>', methods=["GET"])
@auth_views.login_required
def edit(test_room_id):
    test_room = TestRoom.query.get(test_room_id)
    block_list = test_room.block_list.split(';')[:-1]
    start_date = str(test_room.start_date)
    end_date = str(test_room.end_date)
    date = start_date[0:10]
    start_time = start_date[11:16]
    end_time = end_date[11:16]
    imageBuffer = []
    for s in test_room.student_set:
        image_data = s.image
        image = open(str(s.id) + '.jpg', mode='wb')
        image.write(image_data)
        imageBuffer.append(image)
        print(image.name)
        image.close()
    return render_template(f'test_room/edit.html', test_room_id=test_room_id, date=date, start_time=start_time, end_time=end_time, block_list=block_list, imageBuffer=imageBuffer)



