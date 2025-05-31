from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from ..models.models import User, Role, UserProfile, db

users = Blueprint('users', __name__)

def check_admin_permissions(current_user_id):
    """Проверяет, имеет ли пользователь права администратора"""
    user = User.query.get(current_user_id)
    if not user:
        return False
    return 'admin' in [role.name for role in user.roles]

@users.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'phone': user.phone,
        'roles': [role.display_name or role.name for role in user.roles],
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

@users.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Обновление профиля текущего пользователя"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные для обновления не предоставлены'}), 400

    # Обновляем основные данные пользователя
    if 'phone' in data:
        user.phone = data['phone']

    # Обновляем профиль пользователя
    profile_data = data.get('profile', {})
    if profile_data:
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
            db.session.add(user.profile)

        if 'first_name' in profile_data:
            user.profile.first_name = profile_data['first_name']
        if 'last_name' in profile_data:
            user.profile.last_name = profile_data['last_name']
        if 'middle_name' in profile_data:
            user.profile.middle_name = profile_data['middle_name']
        if 'gender' in profile_data:
            user.profile.gender = profile_data['gender']
        if 'department' in profile_data:
            user.profile.department = profile_data['department']
        if 'position' in profile_data:
            user.profile.position = profile_data['position']
        if 'course' in profile_data:
            user.profile.course = profile_data['course']
        if 'group_name' in profile_data:
            user.profile.group_name = profile_data['group_name']
        if 'school' in profile_data:
            user.profile.school = profile_data['school']

    db.session.commit()
    return jsonify({'message': 'Профиль обновлен успешно'}), 200

@users.route('/employees', methods=['GET'])
@jwt_required()
def get_employees():
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для просмотра сотрудников'}), 403

    employee_role = Role.query.filter_by(name='employee').first()
    teacher_role = Role.query.filter_by(name='teacher').first()

    employees = []
    if employee_role:
        employees.extend(employee_role.users)
    if teacher_role:
        employees.extend(teacher_role.users)

    # Удаляем дубликаты пользователей с обеими ролями
    unique_employees = {emp.id: emp for emp in employees}.values()
    result = []
    for emp in unique_employees:
        if emp.profile:
            full_name = f"{emp.profile.last_name or ''} {emp.profile.first_name or ''}".strip()
            if emp.profile.middle_name:
                full_name += f" {emp.profile.middle_name}"
        else:
            full_name = emp.username
        if not full_name:
            full_name = emp.username

        result.append({
            'id': emp.id,
            'name': full_name.strip(),
            'username': emp.username,
            'email': emp.email
        })
    return jsonify(result), 200

@users.route('/all', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для просмотра всех пользователей'}), 403

    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'name': user.username if not user.profile else f"{user.profile.last_name or ''} {user.profile.first_name or ''} {user.profile.middle_name or ''}".strip() or user.username,
        'email': user.email,
        'roles': [{
            'id': role.id,
            'name': role.name,
            'description': role.description
        } for role in user.roles]
    } for user in users])

@users.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    roles = Role.query.all()
    return jsonify([{
        'id': role.id,
        'name': role.name,
        'display_name': role.display_name,
        'description': role.description
    } for role in roles])

@users.route('/roles', methods=['POST'])
@jwt_required()
def create_role():
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для создания ролей'}), 403

    data = request.get_json()
    
    # Проверяем обязательные поля
    if not data or 'name' not in data or 'display_name' not in data:
        return jsonify({'error': 'Системное имя (name) и отображаемое имя (display_name) обязательны'}), 400
        
    # Проверяем существование роли по системному имени
    existing_role = Role.query.filter_by(name=data['name']).first()
    if existing_role:
        return jsonify({'error': 'Роль с таким системным именем уже существует'}), 400
        
    # Создаем новую роль
    new_role = Role(
        name=data['name'],
        display_name=data['display_name'],
        description=data.get('description', '')
    )
    
    db.session.add(new_role)
    db.session.commit()
    
    return jsonify({
        'id': new_role.id,
        'name': new_role.name,
        'display_name': new_role.display_name,
        'description': new_role.description
    }), 201

@users.route('/<int:user_id>/roles', methods=['PUT'])
@jwt_required()
def update_user_roles(user_id):
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для изменения ролей пользователей'}), 403

    data = request.get_json()
    
    if not data or 'role_ids' not in data:
        return jsonify({'error': 'Список ролей обязателен'}), 400
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
        
    roles = Role.query.filter(Role.id.in_(data['role_ids'])).all()
    if len(roles) != len(data['role_ids']):
        return jsonify({'error': 'Некоторые роли не найдены'}), 400
        
    user.roles = roles
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'name': user.username if not user.profile else f"{user.profile.last_name or ''} {user.profile.first_name or ''} {user.profile.middle_name or ''}".strip() or user.username,
        'email': user.email,
        'roles': [{
            'id': role.id,
            'name': role.name,
            'description': role.description
        } for role in user.roles]
    })

@users.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Обновление данных пользователя администратором"""
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для редактирования пользователей'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Данные для обновления не предоставлены'}), 400

    # Обновление основных данных пользователя
    if 'email' in data:
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Пользователь с таким email уже существует'}), 400
        user.email = data['email']

    if 'username' in data:
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Пользователь с таким username уже существует'}), 400
        user.username = data['username']

    if 'phone' in data:
        user.phone = data['phone']

    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])

    # Обновление профиля пользователя
    profile_data = data.get('profile', {})
    if profile_data:
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
            db.session.add(user.profile)

        if 'first_name' in profile_data:
            user.profile.first_name = profile_data['first_name']
        if 'last_name' in profile_data:
            user.profile.last_name = profile_data['last_name']
        if 'middle_name' in profile_data:
            user.profile.middle_name = profile_data['middle_name']
        if 'gender' in profile_data:
            user.profile.gender = profile_data['gender']
        if 'department' in profile_data:
            user.profile.department = profile_data['department']
        if 'position' in profile_data:
            user.profile.position = profile_data['position']
        if 'course' in profile_data:
            user.profile.course = profile_data['course']
        if 'group_name' in profile_data:
            user.profile.group_name = profile_data['group_name']
        if 'school' in profile_data:
            user.profile.school = profile_data['school']

    db.session.commit()
    return jsonify({'message': 'Пользователь обновлен успешно'}), 200

@users.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Удаление пользователя"""
    current_user_id = get_jwt_identity()
    if not check_admin_permissions(current_user_id):
        return jsonify({'error': 'Недостаточно прав для удаления пользователей'}), 403

    # Нельзя удалить самого себя
    if current_user_id == user_id:
        return jsonify({'error': 'Нельзя удалить собственную учетную запись'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Пользователь удален успешно'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при удалении пользователя: {str(e)}'}), 500 