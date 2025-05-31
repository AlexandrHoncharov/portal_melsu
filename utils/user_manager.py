from flask import jsonify
from werkzeug.security import generate_password_hash
from ..models.models import db, User, UserProfile, Role

def create_user(email, username, password, roles=None, profile_data=None, is_verified=True):
    """
    Создает нового пользователя с указанными данными.
    
    Args:
        email (str): Email пользователя
        username (str): Имя пользователя
        password (str): Пароль пользователя
        roles (list): Список имен ролей, которые следует назначить пользователю
        profile_data (dict): Словарь с данными профиля пользователя
        is_verified (bool): Флаг подтверждения email пользователя
        
    Returns:
        tuple: (Созданный пользователь, Сообщение об ошибке)
    """
    try:
        # Проверяем существует ли пользователь с таким email или username
        if User.query.filter_by(email=email).first():
            return None, 'Пользователь с таким email уже существует'
        
        if User.query.filter_by(username=username).first():
            return None, 'Пользователь с таким username уже существует'
            
        # Создаем пользователя
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            is_verified=is_verified
        )
        db.session.add(user)
        db.session.flush()  # Получаем ID пользователя
        
        # Создаем профиль пользователя, если предоставлены данные
        if profile_data:
            profile = UserProfile(
                user_id=user.id,
                first_name=profile_data.get('first_name'),
                last_name=profile_data.get('last_name'),
                middle_name=profile_data.get('middle_name'),
                gender=profile_data.get('gender'),
                department=profile_data.get('department'),
                position=profile_data.get('position'),
                course=profile_data.get('course'),
                group_name=profile_data.get('group_name'),
                school=profile_data.get('school')
            )
            db.session.add(profile)
        
        # Назначаем роли пользователю
        if roles:
            for role_name in roles:
                role = Role.query.filter_by(name=role_name).first()
                if role:
                    user.roles.append(role)
        
        db.session.commit()
        return user, None
        
    except Exception as e:
        db.session.rollback()
        return None, f'Ошибка при создании пользователя: {str(e)}'

def get_user_by_id(user_id):
    """
    Возвращает пользователя по ID
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        User: Объект пользователя или None
    """
    return User.query.get(user_id)

def get_user_by_email(email):
    """
    Возвращает пользователя по email
    
    Args:
        email (str): Email пользователя
        
    Returns:
        User: Объект пользователя или None
    """
    return User.query.filter_by(email=email).first()

def update_user_profile(user, profile_data):
    """
    Обновляет профиль пользователя
    
    Args:
        user (User): Объект пользователя
        profile_data (dict): Данные профиля для обновления
        
    Returns:
        bool: True если обновление успешно, иначе False
    """
    try:
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
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка обновления профиля: {str(e)}")
        return False

def create_admin_user(email, username, password):
    """
    Создает пользователя с правами администратора
    
    Args:
        email (str): Email администратора
        username (str): Имя пользователя администратора
        password (str): Пароль администратора
        
    Returns:
        tuple: (Созданный пользователь, Сообщение об ошибке)
    """
    return create_user(email, username, password, roles=['admin'], is_verified=True)

def get_user_roles(user):
    """
    Возвращает список ролей пользователя
    
    Args:
        user (User): Объект пользователя
        
    Returns:
        list: Список объектов ролей
    """
    return user.roles

def check_user_has_role(user, role_name):
    """
    Проверяет, имеет ли пользователь указанную роль
    
    Args:
        user (User): Объект пользователя
        role_name (str): Имя роли для проверки
        
    Returns:
        bool: True если пользователь имеет роль, иначе False
    """
    return role_name in [role.name for role in user.roles]

def format_user_info(user, include_roles=True):
    """
    Форматирует информацию о пользователе для API
    
    Args:
        user (User): Объект пользователя
        include_roles (bool): Включать ли информацию о ролях
        
    Returns:
        dict: Словарь с информацией о пользователе
    """
    result = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'is_verified': user.is_verified
    }
    
    if include_roles:
        result['roles'] = [{'id': role.id, 'name': role.name, 'display_name': role.display_name} for role in user.roles]
    
    if user.profile:
        names = filter(None, [user.profile.last_name, user.profile.first_name, user.profile.middle_name])
        full_name = ' '.join(names)
        result['full_name'] = full_name if full_name else user.username
        
        result['profile'] = {
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
    else:
        result['full_name'] = user.username
    
    return result 