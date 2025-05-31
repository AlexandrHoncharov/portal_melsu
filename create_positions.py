from app import app
from models.models import db, Position

def create_positions():
    positions = [
        {"name": "Директор", "description": "Руководитель организации"},
        {"name": "Заместитель директора", "description": "Заместитель руководителя организации"},
        {"name": "Начальник отдела", "description": "Руководитель структурного подразделения"},
        {"name": "Специалист", "description": "Специалист подразделения"},
        {"name": "Преподаватель", "description": "Преподаватель образовательного учреждения"}
    ]

    with app.app_context():
        for pos_data in positions:
            # Проверяем, существует ли уже такая должность
            existing = Position.query.filter_by(name=pos_data["name"]).first()
            if not existing:
                position = Position(**pos_data)
                db.session.add(position)
                print(f"Добавлена должность: {pos_data['name']}")
            else:
                print(f"Должность уже существует: {pos_data['name']}")
        
        db.session.commit()
        print("\nВсе должности добавлены успешно!")

if __name__ == "__main__":
    create_positions() 