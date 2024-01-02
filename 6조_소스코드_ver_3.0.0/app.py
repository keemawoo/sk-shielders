
from flask import Flask, render_template, session, url_for, request, redirect, send_file
from werkzeug.utils import secure_filename
import os
import pymysql
import jwt
import secrets
from datetime import datetime, timedelta
from pytz import timezone

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=15)

JWT_SECRET_KEY = secrets.token_bytes(32)

app.config['UPLOAD_FOLDER'] = 'uploads'
def create_upload_folder_if_not_exists():
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

        
app.config['MAX_LOGIN_ATTEMPTS'] = 5  # 최대 로그인 실패 횟수
app.config['LOCKOUT_DURATION'] = timedelta(minutes=10)  # 로그인 잠금 기간

        
ALLOWED_EXTENSIONS = {'pdf', 'jpeg', 'png', 'jpg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def connectsql():
    conn = pymysql.connect(host='dd-database.c2u3lanlszlp.ap-southeast-2.rds.amazonaws.com', user = 'DDadmin', passwd = 'Ekwlagodyd666!', db = 'userlist', charset='utf8')
    return conn


def check_password(input_pw : str) -> bool:
        
    import re            
    pattern = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
    if pattern.match(input_pw):
        return True
    else:
        return False

@app.route('/')
# 세션유지를 통한 로그인 유무 확인
def index():
    if 'user_token' in session:
        # 세션에서 토큰을 가져와서 디코딩
        user_token = session['user_token']
        try:
            user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
        except jwt.ExpiredSignatureError:
            # 토큰이 만료되었을 경우 세션에서 삭제
            session.pop('user_token', None)
            return "토큰이 만료되었습니다. 다시 로그인하세요."
        
        return render_template('index.html', logininfo = user_id)

    return render_template('index.html')

@app.route('/post')
# board테이블의 게시판 제목리스트 역순으로 출력
def post():
    if 'user_token' in session:
        user_token = session['user_token']
        try:
            user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
        except jwt.ExpiredSignatureError:
            session.pop('user_token', None)
            return "토큰이 만료되었습니다. 다시 로그인하세요."
        conn = connectsql()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query = "SELECT id, name, title, wdate, view FROM board WHERE is_deleted = 0 ORDER BY id DESC" 
        cursor.execute(query)
        post_list = cursor.fetchall()
    
        cursor.close()
        conn.close()

        return render_template('post.html', postlist = post_list, logininfo=user_id)
    else:
        return render_template('Error.html')

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
        file_path = '/home/ec2-user/Flask_board_with_AWS/flask/Flask_board_with_AWS/flask_board_with_AWS/uploads/' + filename  # 파일 경로 수정 필요
        response = send_file(file_path, as_attachment=True)
        response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        return response

@app.route('/post/content/<id>')
# 조회수 증가, post페이지의 게시글 클릭시 id와 content 비교 후 게시글 내용 출력
def content(id):
    if 'user_token' in session:
        user_token = session['user_token']
        try:
            user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
        except jwt.ExpiredSignatureError:
            session.pop('user_token', None)
            return "토큰이 만료되었습니다. 다시 로그인하세요."
        conn = connectsql()
        cursor = conn.cursor()
        query = "UPDATE board SET view = view + 1 WHERE id = %s"
        value = id
        cursor.execute(query, value)
        conn.commit()
        cursor.close()
        conn.close()

        conn = connectsql()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        query = "SELECT id, title, content, file_name FROM board WHERE id = %s"
        value = id
        cursor.execute(query, value)
        content_data = cursor.fetchone()  # 단일 게시글 정보 가져오기
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('content.html', data = content_data, username = user_id)
    else:
        return render_template ('Error.html')

@app.route('/post/edit/<id>', methods=['GET', 'POST'])
# GET -> 유지되고있는 username 세션과 현재 접속되어진 id와 일치시 edit페이지 연결
# POST -> 접속되어진 id와 일치하는 title, content를 찾아 UPDATE
def edit(id):
    if request.method == 'POST':
        if 'user_token' in session:
            user_token = session['user_token']
            try:
                user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
            except jwt.ExpiredSignatureError:
                session.pop('user_token', None)
                return "토큰이 만료되었습니다. 다시 로그인하세요."
 
            edittitle = request.form['title']
            editcontent = request.form['content']

            conn = connectsql()
            cursor = conn.cursor()
            query = "UPDATE board SET title = %s, content = %s WHERE id = %s"
            value = (edittitle, editcontent, id)
            cursor.execute(query, value)
            conn.commit()
            cursor.close()
            conn.close()
    
            return render_template('editSuccess.html')
    else:
        if 'user_token' in session:
            user_token = session['user_token']
            try:
                user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
            except jwt.ExpiredSignatureError:
                session.pop('user_token', None)
                return "토큰이 만료되었습니다. 다시 로그인하세요."
            conn = connectsql()
            cursor = conn.cursor()
            query = "SELECT name FROM board WHERE id = %s"
            value = id
            cursor.execute(query, value)
            data = [post[0] for post in cursor.fetchall()]
            cursor.close()
            conn.close()
           
            if user_id in data or user_id == 'DDadmin':
                conn = connectsql()
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                query = "SELECT id, title, content FROM board WHERE id = %s"
                value = id
                cursor.execute(query, value)
                postdata = cursor.fetchall()
                cursor.close()
                conn.close()
                return render_template('edit.html', data=postdata, logininfo=user_id)
            else:
                return render_template('editError.html')
        else:
            return render_template ('Error.html')

@app.route('/post/delete/<id>')
# 유지되고 있는 session_key 세션과 id 일치시 삭제 확인 팝업 연결
def delete(id):
    if 'user_token' in session:
        user_token = session['user_token']
        try:
            user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
        except jwt.ExpiredSignatureError:
            session.pop('user_token', None)
            return "토큰이 만료되었습니다. 다시 로그인하세요."
        conn = connectsql()
        cursor = conn.cursor()
        select_query = "SELECT name FROM board WHERE id = %s"
       # update_query = "UPDATE board SET is_deleted = TRUE WHERE id = %s"
        value = id
        cursor.execute(select_query, (value,))
        data = [post[0] for post in cursor.fetchall()]

        if user_id in data or user_id == 'DDadmin':
           # cursor.execute(update_query, (value,))
           # conn.commit()
           # cursor.close()
           # conn.close()
            
            return render_template('delete.html', id = id)
        else:
            return render_template('editError.html')
    else:
        return render_template ('Error.html')

@app.route('/post/delete/success/<id>')
# 삭제 확인시 id와 일치하는 컬럼 삭제, 취소시 /post 페이지 연결
def deletesuccess(id):
    conn = connectsql()
    cursor = conn.cursor()
    query = "UPDATE board SET is_deleted = TRUE WHERE id = %s"
    value = id
    cursor.execute(query, value)
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('post'))

# 사용자별 게시글 작성 시간을 기록하기 위한 딕셔너리
user_post_times = {}
    
@app.route('/write', methods=['GET', 'POST'])
def write():
    if request.method == 'POST':
        if 'user_token' in session:
            user_token = session['user_token']
            try:
                user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
            except jwt.ExpiredSignatureError:
                session.pop('user_token', None)
                return "토큰이 만료되었습니다. 다시 로그인하세요."
           
            # 사용자가 최근 30분 동안 쓴 게시글 확인
            if user_id in user_post_times:
                recent_post_times = user_post_times[user_id]
                now = datetime.now()
                # 30분 이내의 작성 기록만 남기기
                recent_post_times = [t for t in recent_post_times if now - t <= timedelta(minutes=30)]
                if len(recent_post_times) >= 5:
                    return render_template("postError.html")
            else:
                recent_post_times = []

            usertitle = request.form['title']
            usercontent = request.form['content']
            create_upload_folder_if_not_exists()

            # 파일 업로드 처리
            uploaded_file = request.files['file']
            if uploaded_file:
                if allowed_file(uploaded_file.filename):
                    filename = secure_filename(uploaded_file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    uploaded_file.save(file_path)
                else:
                    return render_template('uploaderror.html')
            else:
                filename = None

            conn = connectsql()
            cursor = conn.cursor()
            query = "INSERT INTO board (name, title, content, file_name) VALUES (%s, %s, %s, %s)"
            value = (user_id, usertitle, usercontent, filename)
            cursor.execute(query, value)
            conn.commit()
            cursor.close()
            conn.close()

            # 사용자의 게시글 작성 시간 기록 업데이트
            recent_post_times.append(datetime.now())
            user_post_times[user_id] = recent_post_times

            return redirect(url_for('post'))
        else:
            return render_template('errorpage.html')
    else:
        if 'user_token' in session:
            user_token = session['user_token']
            try:
                user_id = jwt.decode(user_token, JWT_SECRET_KEY, algorithms=['HS256'])['user_id']
            except jwt.ExpiredSignatureError:
                session.pop('user_token', None)
                return "토큰이 만료되었습니다. 다시 로그인하세요."
           
            # 사용자가 최근 30분 동안 작성한 게시글 수 확인
            if user_id in user_post_times:
                recent_post_times = user_post_times[user_id]
                now = datetime.now()
                # 30분 이내의 작성 기록만 남기기
                recent_post_times = [t for t in recent_post_times if now - t <= timedelta(minutes=30)]
                if len(recent_post_times) >= 5:
                    return render_template("postError.html")
            else:
                recent_post_times = []

            return render_template ('write.html', logininfo = user_id)
        else:
            return render_template ('Error.html')

@app.route('/logout')
# username 세션 해제
def logout():
    if 'user_token' in session:
        session.pop('user_token', None)  # 세션에서 JWT 토큰을 제거
    return redirect(url_for('index'))


#로그인 잠금 상태인지 확인
def is_user_locked_out():
    
    time_now = datetime.now(timezone('Asia/Seoul'))
    
    if 'lockout_time' in session:
        lockout_time = session['lockout_time']
        if time_now < lockout_time:
            return True
        else:
            # 잠금 시간이 지났으면 잠금 상태 해제
            session.pop('lockout_time', None)
            session.pop('login_attempts', None)
            
    return False



@app.route('/login', methods=['GET','POST'])
def login():
    time_now = datetime.now(timezone('Asia/Seoul'))
    
    if is_user_locked_out():
        return render_template ('reset.html')
    
    if request.method == 'POST':
        userid = request.form['id']
        userpw = request.form['pw']
        
        if(len(userid)>20 or len(userpw)>20):    
            return render_template('loginstringError.html')
        
        else:
            conn = connectsql()
            cursor = conn.cursor()
            query = "SELECT * FROM tbl_user WHERE user_name = %s AND user_password = %s"
            value = (userid, userpw)
            cursor.execute(query, value)
            data = cursor.fetchone()  # 단일 레코드만 필요하므로 fetchone 사용
            cursor.close()
            conn.close()
        
            if data:
                # JWT를 사용하여 토큰 생성
                user_token = jwt.encode({'user_id': userid}, JWT_SECRET_KEY, algorithm='HS256')
                
                # 세션에 토큰 저장 (15분간 유지)
                session['user_token'] = user_token
                session.permanent = True  # 세션 유지 설정
                
                session.pop('login_attempts', None)
                
                return redirect(url_for('post'))
            else:
                
                login_attempts = session.get('login_attempts',0) + 1
                session['login_attempts'] = login_attempts
                        
                if login_attempts >= app.config['MAX_LOGIN_ATTEMPTS']:
                    session['lockout_time'] = time_now + app.config['LOCKOUT_DURATION']
                    return render_template ('reset.html')
                
                else:
                    return render_template('loginError.html')
    else:
        return render_template('login.html')

@app.route('/regist', methods=['GET', 'POST'])
def regist():
    if request.method == 'POST':
        userid = request.form['id']
        userpw = request.form['pw']
        
        if(len(userid)>20 or len(userpw)>20):
            return render_template('registstringError.html')
        
        else:
            if check_password(userpw) is True:
                conn = connectsql()
                cursor = conn.cursor()
                query = "SELECT * FROM tbl_user WHERE user_name = %s"
                value = userid
                cursor.execute(query, value)
                data = cursor.fetchone()  # 단일 레코드만 필요하므로 fetchone 사용

                if data:
                    conn.rollback()  # 회원이 이미 존재하면 롤백
                    return render_template('registError.html')
                else:
                    query = "INSERT INTO tbl_user (user_name, user_password) VALUES (%s, %s)"
                    value = (userid, userpw)
                    cursor.execute(query, value)
                    data = cursor.fetchall()
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return render_template('registSuccess.html')
            else:
                return render_template('passwordError.html')
    else:
        return render_template('regist.html')      
       

if __name__ == '__main__':
    #app.run(debug=True)
    app.run('0.0.0.0', port=80, debug=True)
