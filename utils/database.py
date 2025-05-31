from datetime import datetime, timedelta
from ..models.models import db, VerificationCode, RegistrationData, Role

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