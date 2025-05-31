import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.models import db, Role
from backend.app import create_app

app = create_app()

with app.app_context():
    roles = Role.query.all()
    print("\nСписок всех ролей в системе:")
    for role in roles:
        print(f"ID: {role.id}, Название: {role.name}, Отображаемое имя: {role.display_name}")
        print(f"   Описание: {role.description}")
        print("-" * 50) 