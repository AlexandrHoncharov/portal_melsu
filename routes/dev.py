from flask import Blueprint, jsonify, current_app, request
from werkzeug.security import generate_password_hash
from ..models.models import db, User, UserProfile, Role, VerificationCode
from ..utils.database import cleanup_old_records
from ..utils.user_manager import create_admin_user, create_user

dev = Blueprint('dev', __name__)

@dev.route('/email-codes', methods=['GET'])
def dev_email_codes():
    if not current_app.debug:
        return jsonify({'error': 'Route available only in debug mode'}), 403

    codes = VerificationCode.query.order_by(VerificationCode.created_at.desc()).all()
    return jsonify([{
        'email': code.email,
        'code': code.code,
        'created_at': code.created_at.isoformat(),
        'verified': code.verified,
        'expired': code.is_expired()
    } for code in codes]), 200

@dev.route('/test/create-admin', methods=['POST'])
def create_test_admin():
    """
    Создает тестового администратора для разработки
    """
    admin_data = request.get_json() or {}
    
    email = admin_data.get('email', 'admin@melsu.ru')
    username = admin_data.get('username', 'admin')
    password = admin_data.get('password', 'admin123')
    
    admin_user, error = create_admin_user(email, username, password)
    
    if error:
        return jsonify({'error': error}), 400
        
    if admin_user:
        return jsonify({
            'message': 'Тестовый администратор создан',
            'user': {
                'id': admin_user.id,
                'email': admin_user.email,
                'username': admin_user.username
            }
        }), 201
    
    return jsonify({'error': 'Не удалось создать администратора'}), 500

@dev.route('/test/users', methods=['POST'])
def create_test_users():
    """
    Создает тестовых пользователей с различными ролями для разработки
    """
    try:
        # Создаем студента
        student, error = create_user(
            email='student@melsu.ru',
            username='student',
            password='student123',
            roles=['student'],
            profile_data={
                'first_name': 'Иван',
                'last_name': 'Студентов',
                'middle_name': 'Петрович',
                'gender': 'Мужской',
                'course': 2,
                'group_name': 'ИПБ-21'
            }
        )
        
        if error:
            return jsonify({'error': f'Ошибка создания студента: {error}'}), 400
            
        # Создаем преподавателя
        teacher, error = create_user(
            email='teacher@melsu.ru',
            username='teacher',
            password='teacher123',
            roles=['teacher'],
            profile_data={
                'first_name': 'Мария',
                'last_name': 'Преподавателева',
                'middle_name': 'Ивановна',
                'gender': 'Женский',
                'position': 'Доцент'
            }
        )
        
        if error:
            return jsonify({'error': f'Ошибка создания преподавателя: {error}'}), 400
            
        # Создаем сотрудника
        employee, error = create_user(
            email='employee@melsu.ru',
            username='employee',
            password='employee123',
            roles=['employee'],
            profile_data={
                'first_name': 'Петр',
                'last_name': 'Сотрудников',
                'middle_name': 'Сергеевич',
                'gender': 'Мужской',
                'position': 'Специалист'
            }
        )
        
        if error:
            return jsonify({'error': f'Ошибка создания сотрудника: {error}'}), 400
            
        return jsonify({
            'message': 'Тестовые пользователи успешно созданы',
            'users': [
                {
                    'role': 'student',
                    'username': 'student',
                    'password': 'student123',
                    'email': 'student@melsu.ru'
                },
                {
                    'role': 'teacher',
                    'username': 'teacher',
                    'password': 'teacher123',
                    'email': 'teacher@melsu.ru'
                },
                {
                    'role': 'employee',
                    'username': 'employee',
                    'password': 'employee123',
                    'email': 'employee@melsu.ru'
                }
            ]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка создания тестовых пользователей: {str(e)}'}), 500

@dev.route('/test/cleanup', methods=['POST'])
def cleanup_database():
    """
    Очищает базу данных для тестирования
    """
    try:
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        
        # Создаем заново базовые роли
        from ..utils.database import create_default_roles
        create_default_roles()
        
        return jsonify({'message': 'База данных очищена успешно'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при очистке базы данных: {str(e)}'}), 500

@dev.route('/test/status', methods=['GET'])
def check_status():
    """
    Проверяет статус базы данных и возвращает базовую информацию
    """
    try:
        users_count = User.query.count()
        roles = Role.query.all()
        roles_info = [{'id': role.id, 'name': role.name, 'display_name': role.display_name} for role in roles]
        
        return jsonify({
            'status': 'ok',
            'database': {
                'users_count': users_count,
                'roles': roles_info
            },
            'app_config': {
                'testing': current_app.config.get('TESTING', False),
                'debug': current_app.config.get('DEBUG', False)
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка при проверке статуса: {str(e)}'}), 500

@dev.route('/test/create-user', methods=['POST'])
def create_custom_user():
    """
    Создает пользователя с указанными данными
    """
    data = request.get_json() or {}
    
    # Если данные не указаны, используем значения по умолчанию
    email = data.get('email', 'sanumxxx@yandex.ru')
    username = data.get('username', 'sanum')
    password = data.get('password', '111111')
    role_names = data.get('roles', ['student'])
    
    # Создаем профиль
    profile_data = data.get('profile', {
        'first_name': 'Пользователь',
        'last_name': 'Тестовый',
        'gender': 'Мужской'
    })
    
    user, error = create_user(
        email=email,
        username=username,
        password=password,
        roles=role_names,
        profile_data=profile_data,
        is_verified=True
    )
    
    if error:
        return jsonify({'error': error}), 400
        
    if user:
        return jsonify({
            'message': 'Пользователь успешно создан',
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'roles': [role.name for role in user.roles]
            }
        }), 201
    
    return jsonify({'error': 'Не удалось создать пользователя'}), 500 