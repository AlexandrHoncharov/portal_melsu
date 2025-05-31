from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, text
from sqlalchemy.orm import aliased, joinedload
from ..models.models import db, User, Department, Position, department_users

departments = Blueprint('departments', __name__)

@departments.route('/', methods=['GET'])
@jwt_required()
def get_departments():
    """Получение списка всех подразделений"""
    departments = Department.query.all()
    return jsonify([department.to_dict() for department in departments]), 200

@departments.route('/<int:department_id>', methods=['GET'])
@jwt_required()
def get_department(department_id):
    """Получение детальной информации о подразделении"""
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404
    
    # Включаем информацию о пользователях
    return jsonify(department.to_dict(include_users=True)), 200

@departments.route('/', methods=['POST'])
@jwt_required()
def create_department():
    """Создание нового подразделения"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Название подразделения обязательно'}), 400
    
    department = Department(
        name=data['name'],
        short_name=data.get('short_name'),
        description=data.get('description'),
        parent_id=data.get('parent_id'),
        head_user_id=data.get('head_user_id'),
        created_by=current_user_id
    )
    
    db.session.add(department)
    db.session.commit()
    
    return jsonify(department.to_dict()), 201

@departments.route('/<int:department_id>', methods=['PUT'])
@jwt_required()
def update_department(department_id):
    """Обновление информации о подразделении"""
    data = request.get_json()
    department = Department.query.get(department_id)
    
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404
    
    if 'name' in data:
        department.name = data['name']
    if 'short_name' in data:
        department.short_name = data['short_name']
    if 'description' in data:
        department.description = data['description']
    if 'parent_id' in data:
        department.parent_id = data['parent_id']
    if 'head_user_id' in data:
        department.head_user_id = data['head_user_id']
    
    db.session.commit()
    return jsonify(department.to_dict()), 200

@departments.route('/<int:department_id>/users', methods=['POST'])
@jwt_required()
def add_user_to_department(department_id):
    """Добавление пользователя в подразделение"""
    data = request.get_json()
    
    if not data or 'user_id' not in data:
        return jsonify({'error': 'ID пользователя обязателен'}), 400
    
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404
    
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    # Проверяем, не состоит ли пользователь уже в этом подразделении
    existing = db.session.query(department_users).filter_by(
        user_id=user.id, department_id=department.id
    ).first()
    
    if existing:
        # Если состоит, просто обновляем должность, если она указана
        if 'position_id' in data:
            # Используем прямой SQL запрос для обновления
            stmt = text(
                "UPDATE department_users SET position_id = :position_id "
                "WHERE user_id = :user_id AND department_id = :department_id"
            )
            db.session.execute(stmt, {
                'position_id': data['position_id'],
                'user_id': user.id,
                'department_id': department.id
            })
        
        db.session.commit()
        return jsonify({'message': 'Информация обновлена'}), 200
    
    # Если не состоит, добавляем в подразделение
    position_id = data.get('position_id')
    stmt = text(
        "INSERT INTO department_users (user_id, department_id, position_id, created_at) "
        "VALUES (:user_id, :department_id, :position_id, CURRENT_TIMESTAMP)"
    )
    
    db.session.execute(stmt, {
        'user_id': user.id,
        'department_id': department.id,
        'position_id': position_id
    })
    db.session.commit()
    
    return jsonify({'message': 'Пользователь добавлен в подразделение'}), 201

@departments.route('/<int:department_id>/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_user_from_department(department_id, user_id):
    """Удаление пользователя из подразделения"""
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    # Проверяем, состоит ли пользователь в этом подразделении
    existing = db.session.query(department_users).filter_by(
        user_id=user.id, department_id=department.id
    ).first()
    
    if not existing:
        return jsonify({'error': 'Пользователь не состоит в этом подразделении'}), 404
    
    # Удаляем пользователя из подразделения
    stmt = text(
        "DELETE FROM department_users "
        "WHERE user_id = :user_id AND department_id = :department_id"
    )
    
    db.session.execute(stmt, {
        'user_id': user.id,
        'department_id': department.id
    })
    db.session.commit()
    
    return jsonify({'message': 'Пользователь удален из подразделения'}), 200

@departments.route('/positions', methods=['GET'])
@jwt_required()
def get_positions():
    """Получение списка всех должностей"""
    positions = Position.query.all()
    return jsonify([position.to_dict() for position in positions]), 200

@departments.route('/positions', methods=['POST'])
@jwt_required()
def create_position():
    """Создание новой должности"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Название должности обязательно'}), 400
    
    position = Position(
        name=data['name'],
        description=data.get('description')
    )
    
    db.session.add(position)
    db.session.commit()
    
    return jsonify(position.to_dict()), 201

@departments.route('/positions/<int:position_id>', methods=['PUT'])
@jwt_required()
def update_position(position_id):
    """Обновление информации о должности"""
    data = request.get_json()
    position = Position.query.get(position_id)
    
    if not position:
        return jsonify({'error': 'Должность не найдена'}), 404
    
    if 'name' in data:
        position.name = data['name']
    if 'description' in data:
        position.description = data['description']
    
    db.session.commit()
    return jsonify(position.to_dict()), 200

@departments.route('/<int:department_id>/users', methods=['GET'])
@jwt_required()
def get_department_users(department_id):
    """Получение списка пользователей подразделения"""
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'error': 'Подразделение не найдено'}), 404
    
    # Получаем всех пользователей подразделения с их должностями
    stmt = text(
        "SELECT u.id, u.username, u.email, p.first_name, p.last_name, p.middle_name, "
        "du.position_id, du.created_at, pos.name as position_name "
        "FROM user u "
        "LEFT JOIN user_profile p ON u.id = p.user_id "
        "JOIN department_users du ON u.id = du.user_id "
        "LEFT JOIN positions pos ON du.position_id = pos.id "
        "WHERE du.department_id = :department_id"
    )
    
    result = db.session.execute(stmt, {'department_id': department_id})
    users = []
    
    for row in result:
        name = row.username
        if row.first_name or row.last_name:
            name = f"{row.last_name or ''} {row.first_name or ''} {row.middle_name or ''}".strip()
            if not name:
                name = row.username
        
        users.append({
            'user': {
                'id': row.id,
                'name': name,
                'email': row.email
            },
            'position': {
                'id': row.position_id,
                'name': row.position_name
            } if row.position_id else None,
            'created_at': row.created_at if row.created_at else None
        })
    
    return jsonify(users), 200 