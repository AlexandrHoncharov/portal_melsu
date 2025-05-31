import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.models import db, Position
from backend.app import create_app

app = create_app()

with app.app_context():
    positions = Position.query.all()
    print("\nСуществующие должности:")
    for pos in positions:
        print(f"ID: {pos.id}, Название: {pos.name}") 