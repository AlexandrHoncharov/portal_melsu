from app import create_app
from models.models import db, Position, department_users

app = create_app()

with app.app_context():
    print('\nПозиции в базе данных:')
    positions = Position.query.all()
    for pos in positions:
        print(f'ID: {pos.id}, Название: {pos.name}')
        
    print('\nСвязи пользователей с позициями:')
    du = db.session.execute(db.select(department_users)).all()
    for d in du:
        print(f'Department ID: {d.department_id}, User ID: {d.user_id}, Position ID: {d.position_id}') 