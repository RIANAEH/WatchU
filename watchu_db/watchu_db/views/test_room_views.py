import base64
import io
from datetime import datetime

from PIL import Image
from flask import Blueprint, render_template, request, g, url_for, Response, stream_with_context, session, jsonify
from werkzeug.utils import redirect
import secrets

from watchu_db.models import Professor, TestRoom, Student, Log
from watchu_db import db
from watchu_db.views import auth_views

bp = Blueprint('test_room', __name__, url_prefix='/test_room')


@bp.route('/', methods=["GET"])
@bp.route('/menu', methods=["GET"])
@auth_views.login_required
def menu():
    return render_template('test_room/menu.html')


@bp.route('/make', methods=["GET"])
@auth_views.login_required
def make():
    """ 시험 생성 """
    test_room_id = secrets.token_urlsafe(11)
    print(test_room_id)
    return render_template('test_room/make.html', test_room_id=test_room_id)


@bp.route('/make_ajax', methods=['GET', 'POST'])
def make_ajax():
    """ 시험 생성 정보 받기 & 데이터베이스 변경 """
    test_room_id = request.form['test_room_id']
    professor_id = request.form['professor_id']
    block_list = request.form['block_list']
    date = request.form['date'].split('-')
    start = request.form['start_time'].split(':')
    end = request.form['end_time'].split(':')
    start_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(start[0]), int(start[1]))
    end_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(end[0]), int(end[1]))

    # TestRoom 객체 생성
    test_room = TestRoom(
        id=test_room_id,
        professor=Professor.query.get(professor_id),
        block_list=block_list,
        start_date=start_date, end_date=end_date)
    db.session.add(test_room)

    # Student 객체 생성
    length = request.form['length']
    for i in range(int(length)):
        img = request.files[str(i)]
        student_id = img.filename[:8]
        image_data = img.read()
        student = Student(id=student_id, test_room_id=test_room_id, image=image_data)
        db.session.add(student)
    db.session.commit()
    return "Make Ajax Success"


@bp.route('/edit_list', methods=["GET"])
@auth_views.login_required
def edit_list():
    """ 수정 가능한 시험 리스트 """
    professor = Professor.query.get(g.user.id)
    test_room_list = []
    for t in professor.test_room_set:
        test_room_list.append(t.id)
    return render_template('test_room/edit_list.html', test_room_list=test_room_list)


@bp.route('/edit/<string:test_room_id>', methods=["GET"])
@auth_views.login_required
def edit(test_room_id):
    """ 시험 수정 """
    test_room = TestRoom.query.get(test_room_id)
    block_list = test_room.block_list.split(';')[:-1]
    start_date = str(test_room.start_date)
    end_date = str(test_room.end_date)
    date = start_date[0:10]
    start_time = start_date[11:16]
    end_time = end_date[11:16]
    student_list = []
    image_list = []
    for s in test_room.student_set:
        student_list.append(s.id)
        # python의 bytes를 javascript에서 그대로 못 읽어와서... base64 변환 적용
        img = base64.b64encode(s.image).decode()
        image_list.append(img)
    print(student_list)
    print(len(image_list))
    return render_template(f'test_room/edit.html', test_room_id=test_room_id, date=date, start_time=start_time,
                           end_time=end_time, block_list=block_list, student_list=student_list, image_list=image_list)


@bp.route('/edit_ajax', methods=['GET', 'POST'])
def edit_ajax():
    """ 시험 수정 정보 받기 & 데이터베이스 변경 """
    test_room_id = request.form['test_room_id']
    block_list = request.form['block_list']

    date = request.form['date'].split('-')
    start = request.form['start_time'].split(':')
    end = request.form['end_time'].split(':')
    start_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(start[0]), int(start[1]))
    end_date = datetime(int(date[0]), int(date[1]), int(date[2]), int(end[0]), int(end[1]))

    # TestRoom 객체 수정
    test_room = TestRoom.query.get(test_room_id)
    test_room.block_list = block_list
    test_room.start_date = start_date
    test_room.end_date = end_date
    db.session.add(test_room)

    # Student 객체 수정 및 삭제
    length = request.form['length']
    for i in range(int(length)):
        img = request.files[str(i)]
        student_id = img.filename[:8]
        image_data = img.read()
        student = Student.query.filter(Student.id == student_id, Student.test_room_id == test_room_id).first()
        if student is not None:
            student.image = image_data
        else:
            student = Student(id=student_id, test_room_id=test_room_id, image=image_data)
        db.session.add(student)
    db.session.commit()
    return "Edit Ajax Success"


@bp.route('/delete/<string:test_room_id>', methods=["GET"])
def delete(test_room_id):
    """ 시험 삭제 """
    test_room = TestRoom.query.get(test_room_id)
    db.session.delete(test_room)
    db.session.commit()
    return redirect(url_for('test_room.edit_list'))


@bp.route('/watching_list', methods=["GET"])
@auth_views.login_required
def watching_list():
    """ 입장 가능 시험 리스트 """
    professor = Professor.query.get(g.user.id)
    test_room_list = []
    for t in professor.test_room_set:
        test_room_list.append(t.id)
    return render_template('test_room/watching_list.html', test_room_list=test_room_list)


no_screen_image = open('./static/no_screen.png', 'rb').read()
global_images = dict()  # 전체 화면 공유 이미지 저장 딕셔너리


@bp.route('share_screen/<string:test_room_id>/<int:student_id>', methods=['POST'])
def share_screen(test_room_id, student_id):
    """ HTTP로 화면 받기 """
    image = base64.b64decode(request.form["image"])
    global_images[test_room_id][student_id] = image
    img = Image.open(io.BytesIO(image))
    img.save("MyTest1.png")
    return "done!!"


def gen_frames(test_room_id, student_id):
    while True:
        image = global_images[test_room_id][student_id]
        print(student_id, global_images[test_room_id][student_id][:100])
        frame = bytearray(image)
        img = Image.open(io.BytesIO(image))
        img.save("MyTest2.png")
        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n')


@bp.route('/screen_socket_feed/<string:test_room_id>/<int:student_id>')
def screen_socket_feed(test_room_id, student_id):
    return Response(gen_frames(test_room_id, student_id), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route('/watching/<string:test_room_id>', methods=["GET"])
@auth_views.login_required
def watching(test_room_id):
    """ 시험 중 화면 공유 """
    test_room = TestRoom.query.get(test_room_id)
    student_list = []
    images = dict()
    for s in test_room.student_set:
        student_list.append(s.id)
        images[s.id] = no_screen_image
    global_images[test_room_id] = images
    print(test_room_id, student_list)
    return render_template('test_room/watching.html', test_room_id=test_room_id, student_list=student_list)


watching_log_buffer = set()  # 부정행위가 감지 된 학생 번호


@bp.route('watching/log_ajax/<string:test_room_id>', methods=['POST'])
def watching_log_ajax(test_room_id):
    """ 시험 중 부정행위 알림 """
    json_list = []
    json_list.append({"length": len(watching_log_buffer)})
    if len(watching_log_buffer) != 0:
        for student_id in watching_log_buffer:
            json_list.append({"student_id": student_id})
        watching_log_buffer.clear()
        return jsonify(json_list)
    else:
        return jsonify(json_list)


@bp.route('/student_login/<string:test_room_id>/<int:student_id>', methods=['POST'])
def student_login(test_room_id, student_id):
    """ 학생 로그인 (학생 이미지, 시험 시작, 종료, 차단 프로그램 전송) """
    print(test_room_id, student_id)
    json = dict()
    test_room = TestRoom.query.get(test_room_id)
    if test_room is not None:
        json["test_room"] = "yes"
        student = Student.query.filter(Student.id == student_id, Student.test_room_id == test_room_id).first()
        if student is not None:
            json["student"] = "yes"
            # 학생 이미지 전송
            json["student_image"] = base64.b64encode(student.image).decode()
            # 시험 시작, 종료 전송
            json["start_date"] = str(test_room.start_date)
            json["end_date"] = str(test_room.end_date)
            # 차단 프로그램 리스트 전송
            json["block_list"] = test_room.block_list
        else:
            json["student"] = "no"
    else:
        json["test_room"] = "no"
    print(json)
    return jsonify(json)


@bp.route('/log/<string:test_room_id>/<int:student_id>', methods=['POST'])
def log(test_room_id, student_id):
    """ 로그 받기 """
    print(test_room_id, student_id)
    print(request.form["type"])
    type = request.form["type"]
    date = datetime.strptime(request.form["date"], '%Y-%m-%d %H:%M:%S')
    image = request.form["image"]
    watching_log_buffer.add(student_id)  # 부정행위 감지 학생 저장
    watching_detail_log_buffer.append({  # 부정행위 감지 내용 저장
        "type": type,
        "date": date,
        "image": image
    })
    log = None
    # 키보드 입력 부정행위 로그
    if image == "None":
        log = Log(student=Student.query.filter(Student.id == student_id, Student.test_room_id == test_room_id).first(),
                  type=type, date=date)
    # 본인확인 부정행위 로그
    else:
        image = base64.b64decode(image)  # 받은 이미지 base64 디코딩
        log = Log(student=Student.query.filter(Student.id == student_id, Student.test_room_id == test_room_id).first(),
                  type=type, date=date, image=image)
    db.session.add(log)
    db.session.commit()
    return jsonify("로그 잘 받아짐!!")


watching_detail_log_buffer = list()  # 부정행위 로그 내용 저장


@bp.route('/watching_detail/<string:test_room_id>/<int:student_id>')
def watching_detail(test_room_id, student_id):
    """ 시험 중 학생 디테일 (한명 화면 공유, 로그 띄우기) """
    watching_detail_log_buffer.clear()
    log_list = []
    student = Student.query.filter(Student.id == student_id, Student.test_room_id == test_room_id).first()
    for log in student.log_set:
        log_data = dict()
        log_data["type"] = log.type
        log_data["date"] = log.date
        if log.image is None:
            log_data["image"] = "None"
        else:
            log_data["image"] = base64.b64encode(log.image).decode()
        log_list.append(log_data)
    return render_template('test_room/watching_detail.html', test_room_id=test_room_id, student_id=student_id,
                           log_list=log_list)


@bp.route('watching_detail/log_ajax/<string:test_room_id>/<int:student_id>', methods=['POST'])
def watching_detail_log_ajax(test_room_id, student_id):
    """ 시험 디테일에서 학생의 부정행위 로그 업데이트 """
    json_list = [{"length": len(watching_detail_log_buffer)}]
    if len(watching_detail_log_buffer) != 0:
        for log_data in watching_detail_log_buffer:
            json_list.append(log_data)
        watching_detail_log_buffer.clear()
        return jsonify(json_list)
    else:
        return jsonify(json_list)
