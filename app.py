from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import re
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

"""
Создание и конфигурация Flask приложения.
Инициализация расширений: SQLAlchemy, JWTManager, CORS.
"""
app = Flask(__name__)

app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, supports_credentials=True)

app.config['MAIL_SERVER'] = 'email.melsu.ru'
app.config['MAIL_PORT'] = 587  # или 465 для SSL
app.config['MAIL_USERNAME'] = 'help@melsu.ru'
app.config['MAIL_PASSWORD'] = 'fl_92||LII_O0'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'help@melsu.ru'

"""
================= МОДЕЛИ БАЗ ДАННЫХ =================
Этот блок определяет модели SQLAlchemy, используемые для представления
структуры данных приложения в базе данных.
"""

class User(db.Model):
    """
    Основная модель пользователя.

    Атрибуты:
        id (int): Уникальный идентификатор пользователя.
        email (str): Email пользователя, должен быть уникальным.
        username (str): Имя пользователя, должно быть уникальным.
        password_hash (str): Хэш пароля пользователя.
        phone (str, optional): Номер телефона пользователя.
        is_verified (bool): Флаг, указывающий, подтвержден ли email пользователя.
        created_at (datetime): Дата и время создания пользователя.
        last_login (datetime, optional): Дата и время последнего входа пользователя.
        profile (UserProfile): Связанный профиль пользователя (один-к-одному).
        roles (list[Role]): Список ролей, назначенных пользователю (многие-ко-многим).
        created_forms (list[Form]): Список форм, созданных пользователем (один-ко-многим).
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    roles = db.relationship('Role', secondary='user_roles', backref='users')
    created_forms = db.relationship('Form', backref='creator')


class UserProfile(db.Model):
    """
    Профиль пользователя с дополнительной информацией.

    Атрибуты:
        id (int): Уникальный идентификатор профиля.
        user_id (int): Внешний ключ к таблице 'user'.
        first_name (str, optional): Имя пользователя.
        last_name (str, optional): Фамилия пользователя.
        middle_name (str, optional): Отчество пользователя.
        birth_date (date, optional): Дата рождения пользователя.
        gender (str, optional): Пол пользователя.
        department (str, optional): Отдел (для сотрудников).
        position (str, optional): Должность (для сотрудников).
        course (int, optional): Курс (для студентов).
        group_name (str, optional): Название группы (для студентов).
        school (str, optional): Школа (для школьников).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))

    department = db.Column(db.String(100))  # для сотрудников
    position = db.Column(db.String(100))  # для сотрудников
    course = db.Column(db.Integer)  # для студентов
    group_name = db.Column(db.String(20))  # для студентов
    school = db.Column(db.String(200))  # для школьников


class Role(db.Model):
    """
    Роли пользователей в системе.

    Атрибуты:
        id (int): Уникальный идентификатор роли.
        name (str): Системное имя роли (например, 'student', 'teacher'), уникальное.
        display_name (str, optional): Отображаемое имя роли (например, 'Студент').
        description (str, optional): Описание роли.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    description = db.Column(db.Text)


'''
    Промежуточная таблица для связи многие-ко-многим между пользователями и ролями.
    '''

user_roles = db.Table('user_roles',

    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class VerificationCode(db.Model):
    """
    Модель для временного хранения кодов подтверждения email.

    Атрибуты:
        id (int): Уникальный идентификатор записи.
        email (str): Email, на который отправлен код.
        code (str): 6-значный код подтверждения.
        created_at (datetime): Дата и время создания кода.
        verified (bool): Флаг, указывающий, был ли код использован для подтверждения.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)

    def is_expired(self):
        """Проверяет, истек ли срок действия кода (10 минут)."""
        return (datetime.utcnow() - self.created_at).total_seconds() > 600


class RegistrationData(db.Model):
    """
    Модель для временного хранения данных регистрации между шагами.

    Атрибуты:
        id (int): Уникальный идентификатор записи.
        email (str): Email пользователя, проходящего регистрацию.
        data (str): JSON-строка с данными регистрации.
        created_at (datetime): Дата и время создания записи.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        """Проверяет, истек ли срок хранения данных (1 час)."""
        return (datetime.utcnow() - self.created_at).total_seconds() > 3600


class Form(db.Model):
    """
    Модель для созданных форм (например, отчеты или заявки).

    Атрибуты:
        id (int): Уникальный идентификатор формы.
        name (str): Название формы.
        description (str, optional): Описание формы.
        form_type (str, optional): Тип формы ('отчеты' или 'заявки').
        responsible (str, optional): Ответственный за форму.
        period (str, optional): Периодичность формы.
        fields (str): JSON-строка, описывающая поля формы.
        created_by (int): Внешний ключ к 'user.id', указывающий на создателя формы.
        created_at (datetime): Дата и время создания формы.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    form_type = db.Column(db.String(50))
    responsible = db.Column(db.String(100))
    period = db.Column(db.String(50))
    fields = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Department(db.Model):
    """
    Модель структурных подразделений университета.

    Атрибуты:
        id (int): Уникальный идентификатор подразделения.
        name (str): Полное название подразделения.
        short_name (str, optional): Краткое название подразделения.
        description (str, optional): Описание подразделения.
        parent_id (int, optional): Внешний ключ к 'department.id' (родительское подразделение).
        head_user_id (int, optional): Внешний ключ к 'user.id' (руководитель подразделения).
        created_by (int, optional): Внешний ключ к 'user.id' (создатель записи о подразделении).
        created_at (datetime): Дата и время создания записи.
        parent (Department): Связь с родительским подразделением.
        children (list[Department]): Список дочерних подразделений.
        head (User): Пользователь, являющийся руководителем подразделения.
        creator (User): Пользователь, создавший запись о подразделении.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    short_name = db.Column(db.String(50))
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    head_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Department', remote_side=[id], backref='children')
    head = db.relationship('User', foreign_keys=[head_user_id], backref='headed_departments')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_departments')


"""
================= УТИЛИТЫ =================
Вспомогательные функции, используемые в различных частях приложения.
"""

@app.route('/api/dev/email-codes', methods=['GET'])
def dev_email_codes():
    """Маршрут для просмотра кодов подтверждения (только для разработки)"""
    if not app.debug:
        return jsonify({'error': 'Route available only in debug mode'}), 403
        
    codes = VerificationCode.query.order_by(VerificationCode.created_at.desc()).all()
    return jsonify([{
        'email': code.email,
        'code': code.code,
        'created_at': code.created_at.isoformat(),
        'verified': code.verified,
        'expired': code.is_expired()
    } for code in codes]), 200

def generate_verification_code():
    """Генерирует случайный 5-значный цифровой код."""
    return str(secrets.randbelow(100000)).zfill(5)


def send_verification_email(email, code):
    """
    Отправляет код подтверждения на указанный email через SMTP сервер.

    Args:
        email (str): Email получателя
        code (str): Код подтверждения

    Returns:
        bool: True если отправка успешна, False в случае ошибки
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        msg['Subject'] = 'Код подтверждения для портала МарГУ'

        html = f"""
        <html>
            <body>
                <h2>Код подтверждения</h2>
                <p>Ваш код для подтверждения регистрации: <b>{code}</b></p>
                <p>Код действителен в течение 10 минут.</p>
                <hr>
                <small>Это автоматическое сообщение, не отвечайте на него.</small>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config['MAIL_USE_TLS']:
                server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        print(f"📧 Код {code} успешно отправлен на {email}")
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки email: {e}")
        return False

def cleanup_old_records():
    """
    Удаляет устаревшие записи кодов подтверждения и временных данных регистрации
    из базы данных для поддержания чистоты и производительности.
    """
    try:
        old_codes = VerificationCode.query.filter(
            VerificationCode.created_at < datetime.utcnow() - timedelta(hours=1)
        ).all()
        for code in old_codes:
            db.session.delete(code)

        old_data = RegistrationData.query.filter(
            RegistrationData.created_at < datetime.utcnow() - timedelta(hours=2)
        ).all()
        for data in old_data:
            db.session.delete(data)

        db.session.commit()
        print("🧹 Старые записи очищены")
    except Exception as e:
        print(f"❌ Ошибка очистки данных: {e}")
        db.session.rollback()


def create_default_roles():
    """
    Создает предопределенные роли пользователей в системе, если они еще не существуют.
    Вызывается при инициализации приложения.
    """
    roles_data = [
        {'name': 'student', 'display_name': 'Студент', 'description': 'Обучающийся студент'},
        {'name': 'teacher', 'display_name': 'Преподаватель', 'description': 'Преподавательский состав'},
        {'name': 'employee', 'display_name': 'Сотрудник', 'description': 'Сотрудник университета'},
        {'name': 'schoolboy', 'display_name': 'Школьник', 'description': 'Учащийся школы'},
        {'name': 'admin', 'display_name': 'Админ', 'description': 'Администратор системы'}
    ]

    for role_data in roles_data:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(**role_data)
            db.session.add(role)

    db.session.commit()
    print("✅ Базовые роли созданы")


"""
================= API РЕГИСТРАЦИИ =================
Эндпоинты, отвечающие за многошаговый процесс регистрации новых пользователей.
"""

@app.route('/api/auth/register-step1', methods=['POST'])
def register_step1():
    """
    Шаг 1 регистрации: Прием email и отправка кода подтверждения.

    Принимает JSON: {'email': 'user@example.com'}
    Отправляет код подтверждения на указанный email (имитация).
    Сохраняет код в базе данных.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    data = request.get_json()
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email обязателен'}), 400

    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'error': 'Неверный формат email'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Пользователь с таким email уже существует'}), 400

    cleanup_old_records()
    verification_code = generate_verification_code()
    VerificationCode.query.filter_by(email=email).delete()
    new_code = VerificationCode(email=email, code=verification_code)
    db.session.add(new_code)
    db.session.commit()
    send_verification_email(email, verification_code)

    print(f"📝 Создан код {verification_code} для {email}")
    return jsonify({'message': 'Код отправлен на email'}), 200


@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """
    Шаг 2 регистрации: Проверка кода подтверждения.

    Принимает JSON: {'email': 'user@example.com', 'code': '12345'}
    Проверяет предоставленный код на соответствие и срок действия.

    Returns:
        JSON: Сообщение об успехе (код подтвержден) или ошибке.
    """
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')

    print(f"🔍 Проверяем код {code} для {email}")

    if not email or not code:
        return jsonify({'error': 'Email и код обязательны'}), 400

    verification = VerificationCode.query.filter_by(
        email=email,
        code=code,
        verified=False
    ).first()

    if not verification:
        print(f"❌ Код не найден или уже использован")
        all_codes = VerificationCode.query.filter_by(email=email).all()
        print(f"📋 Все коды для {email}:")
        for vc in all_codes:
            print(f"   - {vc.code} (verified: {vc.verified}, created: {vc.created_at})")
        return jsonify({'error': 'Неверный код'}), 400

    if verification.is_expired():
        print(f"⏰ Код истек")
        db.session.delete(verification)
        db.session.commit()
        return jsonify({'error': 'Код истек'}), 400

    verification.verified = True
    db.session.commit()

    print(f"✅ Код подтвержден для {email}")
    return jsonify({'message': 'Код подтвержден'}), 200


@app.route('/api/auth/resend-code', methods=['POST'])
def resend_code():
    """
    Повторная отправка кода подтверждения.

    Принимает JSON: {'email': 'user@example.com'}
    Генерирует новый код, удаляет старые для этого email и "отправляет" новый.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    data = request.get_json()
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email обязателен'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Пользователь с таким email уже существует'}), 400

    verification_code = generate_verification_code()
    VerificationCode.query.filter_by(email=email).delete()
    new_code = VerificationCode(email=email, code=verification_code)
    db.session.add(new_code)
    db.session.commit()
    send_verification_email(email, verification_code)

    print(f"🔄 Повторно отправлен код {verification_code} для {email}")
    return jsonify({'message': 'Новый код отправлен'}), 200


@app.route('/api/auth/register-step3', methods=['POST'])
def register_step3():
    """
    Шаг 3 регистрации: Ввод username и пароля.

    Принимает JSON: {'email': 'user@example.com', 'username': 'user1', 'password': 'password123'}
    Проверяет, подтвержден ли email, уникальность username.
    Сохраняет эти данные во временное хранилище.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not all([email, username, password]):
        return jsonify({'error': 'Все поля обязательны'}), 400

    verification = VerificationCode.query.filter_by(email=email, verified=True).first()
    if not verification:
        return jsonify({'error': 'Email не подтвержден'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Пользователь с таким username уже существует'}), 400

    RegistrationData.query.filter_by(email=email).delete()
    reg_data = RegistrationData(
        email=email,
        data=json.dumps({
            'email': email,
            'username': username,
            'password': password
        })
    )
    db.session.add(reg_data)
    db.session.commit()

    print(f"💾 Сохранены базовые данные для {email}")
    return jsonify({'message': 'Данные сохранены'}), 200


@app.route('/api/auth/register-step4', methods=['POST'])
def register_step4():
    """
    Шаг 4 регистрации: Ввод личных данных (ФИО, дата рождения, пол).

    Принимает JSON: {'email': 'user@example.com', 'first_name': 'Иван', ...}
    Обновляет временные данные регистрации этой информацией.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    data = request.get_json()
    email = data.get('email')

    reg_data = RegistrationData.query.filter_by(email=email).first()
    if not reg_data or reg_data.is_expired():
        return jsonify({'error': 'Данные пользователя не найдены или истекли'}), 400

    user_data = json.loads(reg_data.data)
    user_data.update({
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'middle_name': data.get('middle_name'),
        'birth_date': data.get('birth_date'),
        'gender': data.get('gender')
    })

    reg_data.data = json.dumps(user_data)
    db.session.commit()

    print(f"👤 Сохранены личные данные для {email}")
    return jsonify({'message': 'Личные данные сохранены'}), 200


@app.route('/api/auth/register-complete', methods=['POST'])
def register_complete():
    """
    Шаг 5 регистрации: Выбор ролей и окончательное создание пользователя.

    Принимает JSON: {'email': 'user@example.com', 'roles': ['Студент', 'Школьник']}
    Создает пользователя, его профиль, назначает роли на основе всех собранных данных.
    Удаляет временные данные регистрации и коды подтверждения.

    Returns:
        JSON: Сообщение об успешной регистрации или ошибке.
    """
    data = request.get_json()
    email = data.get('email')
    selected_roles = data.get('roles', [])

    reg_data = RegistrationData.query.filter_by(email=email).first()
    if not reg_data or reg_data.is_expired():
        return jsonify({'error': 'Данные пользователя не найдены или истекли'}), 400

    user_data = json.loads(reg_data.data)

    try:
        user = User(
            email=user_data['email'],
            username=user_data['username'],
            password_hash=generate_password_hash(user_data['password']),
            is_verified=True
        )
        db.session.add(user)
        db.session.flush()

        profile = UserProfile(
            user_id=user.id,
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            middle_name=user_data.get('middle_name'),
            gender=user_data.get('gender')
        )
        if user_data.get('birth_date'):
            try:
                profile.birth_date = datetime.strptime(user_data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        db.session.add(profile)

        for role_display in selected_roles:
            role = Role.query.filter_by(display_name=role_display).first()
            if role:
                user.roles.append(role)

        db.session.commit()
        VerificationCode.query.filter_by(email=email).delete()
        RegistrationData.query.filter_by(email=email).delete()
        db.session.commit()

        print(f"🎉 Пользователь {user.username} успешно зарегистрирован")
        return jsonify({'message': 'Регистрация завершена'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка создания пользователя: {e}")
        return jsonify({'error': 'Ошибка создания пользователя'}), 500


"""
================= API АВТОРИЗАЦИИ =================
Эндпоинты для входа существующих пользователей и обновления токенов.
"""

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Авторизация пользователя.

    Принимает JSON: {'email': 'user@example.com', 'password': 'password123'}
    Проверяет учетные данные, верификацию email.
    В случае успеха возвращает access и refresh токены, а также информацию о пользователе.

    Returns:
        JSON: Токены и данные пользователя или сообщение об ошибке.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email и пароль обязательны'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Неверный email или пароль'}), 401

    if not user.is_verified:
        return jsonify({'error': 'Email не подтвержден'}), 401

    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    user_roles = [role.display_name for role in user.roles]

    response_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'roles': user_roles,
            'profile': None
        }
    }

    if user.profile:
        response_data['user']['profile'] = {
            'first_name': user.profile.first_name,
            'last_name': user.profile.last_name,
            'middle_name': user.profile.middle_name,
        }

    print(f"🔑 Пользователь {user.username} авторизован")
    return jsonify(response_data), 200


@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Обновление access токена с использованием refresh токена.
    Требует валидный refresh токен в заголовке Authorization.

    Returns:
        JSON: {'access_token': 'new_access_token'}
    """
    current_user_id = get_jwt_identity()
    new_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': new_token})


"""
================= API ПОЛЬЗОВАТЕЛЯ =================
Эндпоинты для получения информации о текущем пользователе.
"""

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Получение профиля текущего авторизованного пользователя.
    Требует валидный access токен.

    Returns:
        JSON: Подробная информация о пользователе и его профиле.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'phone': user.phone,
        'roles': [role.display_name for role in user.roles],
        'full_name': None,
        'birth_date': None
    }

    if user.profile:
        names = [user.profile.last_name, user.profile.first_name, user.profile.middle_name]
        user_data['full_name'] = ' '.join(filter(None, names))

        if user.profile.birth_date:
            months = [
                'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
            ]
            day = user.profile.birth_date.day
            month = months[user.profile.birth_date.month - 1]
            year = user.profile.birth_date.year
            user_data['birth_date'] = f"{day} {month} {year} г."

        user_data['profile'] = {
            'first_name': user.profile.first_name,
            'last_name': user.profile.last_name,
            'middle_name': user.profile.middle_name,
            'gender': user.profile.gender,
            'department': user.profile.department,
            'position': user.profile.position,
            'course': user.profile.course,
            'group_name': user.profile.group_name,
            'school': user.profile.school
        }

    return jsonify(user_data), 200


"""
================= API ФОРМ =================
Эндпоинты для управления формами (отчеты/заявки).
Доступно только для администраторов.
"""

@app.route('/api/forms', methods=['GET'])
@jwt_required()
def get_forms():
    """
    Получение списка всех созданных форм.
    Доступно только пользователям с ролью 'admin'.

    Returns:
        JSON: Список форм с их атрибутами.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    forms = Form.query.all()
    forms_data = []
    for form in forms:
        fields = json.loads(form.fields) if form.fields else []
        forms_data.append({
            'id': form.id,
            'name': form.name,
            'description': form.description,
            'type': form.form_type,
            'responsible': form.responsible,
            'period': form.period,
            'fields': fields,
            'create': form.created_at.strftime('%d.%m.%Y'),
            'status': 'Активна'
        })
    return jsonify(forms_data), 200


@app.route('/api/forms', methods=['POST'])
@jwt_required()
def create_form():
    """
    Создание новой формы.
    Доступно только пользователям с ролью 'admin'.
    Принимает JSON с данными формы: name, description, type, responsible, period, fields.

    Returns:
        JSON: ID созданной формы и сообщение об успехе или ошибке.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    try:
        form = Form(
            name=data.get('name'),
            description=data.get('description'),
            form_type=data.get('type'),
            responsible=data.get('responsible'),
            period=data.get('period'),
            fields=json.dumps(data.get('fields', [])),
            created_by=current_user_id
        )
        db.session.add(form)
        db.session.commit()

        print(f"📄 Создана форма '{form.name}' пользователем {user.username}")
        return jsonify({
            'id': form.id,
            'message': 'Форма создана'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка создания формы: {e}")
        return jsonify({'error': 'Ошибка создания формы'}), 500


@app.route('/api/forms/<int:form_id>', methods=['DELETE'])
@jwt_required()
def delete_form(form_id):
    """
    Удаление формы по ее ID.
    Доступно только пользователям с ролью 'admin'.

    Args:
        form_id (int): Идентификатор удаляемой формы.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    form = Form.query.get(form_id)
    if not form:
        return jsonify({'error': 'Форма не найдена'}), 404

    try:
        form_name = form.name
        db.session.delete(form)
        db.session.commit()

        print(f"🗑️ Удалена форма '{form_name}' пользователем {user.username}")
        return jsonify({'message': 'Форма удалена'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка удаления формы: {e}")
        return jsonify({'error': 'Ошибка удаления формы'}), 500


"""
================= API СТРУКТУРЫ =================
Эндпоинты для управления структурными подразделениями университета.
Доступно только для администраторов.
"""

@app.route('/api/departments', methods=['GET'])
@jwt_required()
def get_departments():
    """
    Получение иерархической структуры всех подразделений.
    Доступно только пользователям с ролью 'admin'.

    Returns:
        JSON: Древовидная структура подразделений.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    departments = Department.query.all()

    def build_tree(parent_id=None):
        result = []
        for dept in departments:
            if dept.parent_id == parent_id:
                dept_data = {
                    'id': dept.id,
                    'name': dept.name,
                    'short_name': dept.short_name,
                    'description': dept.description,
                    'parent_id': dept.parent_id,
                    'head': {
                        'id': dept.head.id,
                        'name': f"{dept.head.profile.last_name} {dept.head.profile.first_name}" if dept.head and dept.head.profile else None
                    } if dept.head else None,
                    'children': build_tree(dept.id),
                    'created_at': dept.created_at.strftime('%d.%m.%Y')
                }
                result.append(dept_data)
        return result

    tree = build_tree()
    return jsonify(tree), 200


@app.route('/api/departments', methods=['POST'])
@jwt_required()
def create_department():
    """
    Создание нового структурного подразделения.
    Доступно только пользователям с ролью 'admin'.
    Принимает JSON с данными подразделения: name, short_name, description, parent_id, head_user_id.

    Returns:
        JSON: ID созданного подразделения и сообщение об успехе или ошибке.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    try:
        department = Department(
            name=data.get('name'),
            short_name=data.get('short_name'),
            description=data.get('description'),
            parent_id=data.get('parent_id') if data.get('parent_id') else None,
            head_user_id=data.get('head_user_id') if data.get('head_user_id') else None,
            created_by=current_user_id
        )
        db.session.add(department)
        db.session.commit()

        print(f"🏢 Создано подразделение '{department.name}' пользователем {user.username}")
        return jsonify({
            'id': department.id,
            'message': 'Подразделение создано'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка создания подразделения: {e}")
        return jsonify({'error': 'Ошибка создания подразделения'}), 500


@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
@jwt_required()
def update_department(dept_id):
    """
    Обновление существующего структурного подразделения.
    Доступно только пользователям с ролью 'admin'.
    Принимает JSON с обновляемыми данными.

    Args:
        dept_id (int): Идентификатор обновляемого подразделения.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    department = Department.query.get(dept_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404

    data = request.get_json()
    try:
        department.name = data.get('name', department.name)
        department.short_name = data.get('short_name', department.short_name)
        department.description = data.get('description', department.description)
        department.parent_id = data.get('parent_id') if data.get('parent_id') is not None else department.parent_id # Allow setting parent_id to None
        department.head_user_id = data.get('head_user_id') if data.get('head_user_id') is not None else department.head_user_id # Allow setting head_user_id to None

        db.session.commit()
        print(f"✏️ Обновлено подразделение '{department.name}'")
        return jsonify({'message': 'Подразделение обновлено'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка обновления подразделения: {e}")
        return jsonify({'error': 'Ошибка обновления подразделения'}), 500


@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@jwt_required()
def delete_department(dept_id):
    """
    Удаление структурного подразделения.
    Доступно только пользователям с ролью 'admin'.
    Нельзя удалить подразделение, если у него есть дочерние элементы.

    Args:
        dept_id (int): Идентификатор удаляемого подразделения.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    department = Department.query.get(dept_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404

    if department.children:
        return jsonify({'error': 'Нельзя удалить подразделение с дочерними элементами'}), 400

    try:
        dept_name = department.name
        db.session.delete(department)
        db.session.commit()

        print(f"🗑️ Удалено подразделение '{dept_name}'")
        return jsonify({'message': 'Подразделение удалено'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка удаления подразделения: {e}")
        return jsonify({'error': 'Ошибка удаления подразделения'}), 500


@app.route('/api/users/employees', methods=['GET'])
@jwt_required()
def get_employees():
    """
    Получение списка сотрудников и преподавателей.
    Используется, например, для выбора руководителя подразделения.
    Доступно только пользователям с ролью 'admin'.

    Returns:
        JSON: Список пользователей с ролями 'employee' или 'teacher'.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    employee_role = Role.query.filter_by(name='employee').first()
    teacher_role = Role.query.filter_by(name='teacher').first()

    employees = []
    if employee_role:
        employees.extend(employee_role.users)
    if teacher_role:
        employees.extend(teacher_role.users)

    unique_employees = {emp.id: emp for emp in employees}.values()
    result = []
    for emp in unique_employees:
        if emp.profile:
            full_name = f"{emp.profile.last_name or ''} {emp.profile.first_name or ''}".strip()
            if emp.profile.middle_name:
                full_name += f" {emp.profile.middle_name}"
        else:
            full_name = emp.username
        if not full_name: # Fallback if profile names are empty
            full_name = emp.username


        result.append({
            'id': emp.id,
            'name': full_name.strip(),
            'username': emp.username,
            'email': emp.email
        })
    return jsonify(result), 200


"""
================= УТИЛИТЫ ДЛЯ РАЗРАБОТКИ =================
Эндпоинты, предназначенные для помощи в разработке и тестировании.
Не должны использоваться в производственной среде без должной защиты.
"""

@app.route('/api/test/create-admin', methods=['POST'])
def create_test_admin():
    """
    Создает тестового пользователя с правами администратора.
    Используется для первоначальной настройки или тестирования.

    Returns:
        JSON: Данные созданного админа или сообщение об ошибке.
    """
    if User.query.filter_by(username='admin').first():
        return jsonify({'error': 'Админ уже существует'}), 400

    try:
        admin = User(
            email='admin@university.ru',
            username='admin',
            password_hash=generate_password_hash('admin123'),
            is_verified=True
        )
        db.session.add(admin)
        db.session.flush()

        profile = UserProfile(
            user_id=admin.id,
            first_name='Админ',
            last_name='Системы',
            middle_name='Админович'
        )
        db.session.add(profile)

        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            admin.roles.append(admin_role)

        db.session.commit()

        print("👑 Создан тестовый администратор")
        return jsonify({
            'message': 'Тестовый админ создан',
            'email': 'admin@university.ru',
            'password': 'admin123'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка создания админа: {e}")
        return jsonify({'error': 'Ошибка создания админа'}), 500


@app.route('/api/test/cleanup', methods=['POST'])
def cleanup_database():
    """
    Выполняет очистку устаревших временных данных из базы.
    Полезно для поддержания чистоты БД во время разработки.

    Returns:
        JSON: Сообщение об успехе или ошибке.
    """
    try:
        cleanup_old_records()
        return jsonify({'message': 'База данных очищена'}), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка очистки: {e}'}), 500


"""
================= ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ =================
Этот блок выполняется при запуске скрипта напрямую.
Создает таблицы базы данных, базовые роли и очищает устаревшие записи.
Запускает Flask development server.
"""
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("🗄️ База данных инициализирована")

        create_default_roles()
        cleanup_old_records()

    print("🚀 Сервер запущен на http://localhost:5000")
    print("📋 Для создания тестового админа: POST /api/test/create-admin")
    print("🧹 Для очистки базы: POST /api/test/cleanup")

    app.run(debug=True, port=5000, host='0.0.0.0')