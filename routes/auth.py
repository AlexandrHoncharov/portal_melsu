import re
import json
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime

from ..models.models import db, User, UserProfile, Role, VerificationCode, RegistrationData
from ..utils.email import generate_verification_code, send_verification_email
from ..utils.database import cleanup_old_records

auth = Blueprint('auth', __name__)

@auth.route('/register-step1', methods=['POST'])
def register_step1():
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

@auth.route('/verify-code', methods=['POST'])
def verify_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({'error': 'Email и код обязательны'}), 400

    verification = VerificationCode.query.filter_by(
        email=email,
        code=code,
        verified=False
    ).first()

    if not verification:
        return jsonify({'error': 'Неверный код'}), 400

    if verification.is_expired():
        db.session.delete(verification)
        db.session.commit()
        return jsonify({'error': 'Код истек'}), 400

    verification.verified = True
    db.session.commit()
    return jsonify({'message': 'Код подтвержден'}), 200

@auth.route('/resend-code', methods=['POST'])
def resend_code():
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

    return jsonify({'message': 'Новый код отправлен'}), 200

@auth.route('/register-step3', methods=['POST'])
def register_step3():
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

    return jsonify({'message': 'Данные сохранены'}), 200

@auth.route('/register-step4', methods=['POST'])
def register_step4():
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

    return jsonify({'message': 'Личные данные сохранены'}), 200

@auth.route('/register-complete', methods=['POST'])
def register_complete():
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

        return jsonify({'message': 'Регистрация завершена'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка создания пользователя'}), 500

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Не предоставлены данные для входа'}), 400
        
    email = data.get('email')
    password = data.get('password')

    # Диагностическое сообщение
    print(f"🔑 Попытка входа: {email}")

    if not email or not password:
        return jsonify({'error': 'Email и пароль обязательны'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        print(f"❌ Пользователь с email {email} не найден")
        return jsonify({'error': 'Неверный email или пароль'}), 401

    if not check_password_hash(user.password_hash, password):
        print(f"❌ Неверный пароль для пользователя {email}")
        return jsonify({'error': 'Неверный email или пароль'}), 401

    if not user.is_verified:
        print(f"❌ Пользователь {email} не подтвержден")
        return jsonify({'error': 'Email не подтвержден'}), 401

    user.last_login = datetime.utcnow()
    db.session.commit()

    # Создаем токены доступа с правильными настройками
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    user_roles = [role.display_name or role.name for role in user.roles]

    print(f"✅ Успешный вход: {email} (роли: {', '.join(user_roles)})")

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

    return jsonify(response_data), 200

@auth.route('/check-token', methods=['GET'])
@jwt_required()
def check_token():
    """
    Проверяет валидность токена и возвращает информацию о пользователе
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
            
        user_data = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'roles': [role.display_name or role.name for role in user.roles],
        }
        
        if user.profile:
            user_data['profile'] = {
                'first_name': user.profile.first_name,
                'last_name': user.profile.last_name,
                'middle_name': user.profile.middle_name,
            }
            
        return jsonify({
            'status': 'valid',
            'user': user_data
        }), 200
        
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {str(e)}")
        return jsonify({'error': 'Ошибка проверки токена'}), 401

@auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Обновляет access token используя refresh token
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404
            
        # Создаем новый access token
        new_access_token = create_access_token(identity=current_user_id)
        
        print(f"🔄 Токен обновлен для пользователя: {user.email}")
        
        return jsonify({
            'access_token': new_access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'roles': [role.display_name or role.name for role in user.roles]
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Ошибка обновления токена: {str(e)}")
        return jsonify({'error': 'Ошибка обновления токена'}), 401 