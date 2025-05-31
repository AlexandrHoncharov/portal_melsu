from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    roles = db.relationship('Role', secondary='user_roles', backref='users')
    created_forms = db.relationship('Form', backref='creator')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': f"{self.profile.last_name} {self.profile.first_name} {self.profile.middle_name}".strip() if self.profile else self.username
        }

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    course = db.Column(db.Integer)
    group_name = db.Column(db.String(20))
    school = db.Column(db.String(200))

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    description = db.Column(db.Text)

user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)

    def is_expired(self):
        return (datetime.utcnow() - self.created_at).total_seconds() > 600

class RegistrationData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        return (datetime.utcnow() - self.created_at).total_seconds() > 3600

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    form_type = db.Column(db.String(50))
    responsible = db.Column(db.String(100))
    period = db.Column(db.String(50))
    fields = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Таблица связи пользователей с подразделениями и должностями
department_users = db.Table('department_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id'), primary_key=True),
    db.Column('position_id', db.Integer, db.ForeignKey('positions.id')),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    short_name = db.Column(db.String(50))
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    head_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    parent = db.relationship('Department', remote_side=[id], backref=db.backref('children', lazy='dynamic'))
    head = db.relationship('User', foreign_keys=[head_user_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    
    # Исправленная связь с пользователями
    users = db.relationship('User', 
                          secondary=department_users,
                          backref=db.backref('department_memberships', lazy='dynamic'))
    
    def to_dict(self, include_users=False):
        result = {
            'id': self.id,
            'name': self.name,
            'short_name': self.short_name,
            'description': self.description,
            'parent_id': self.parent_id,
            'head': self.head.to_dict() if self.head else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': self.creator.to_dict() if self.creator else None,
            'children': [child.to_dict() for child in self.children]
        }
        if include_users:
            result['users'] = []
            for user in self.users:
                user_position = None
                # Получаем должность пользователя в этом департаменте
                department_user = db.session.query(department_users).filter(
                    department_users.c.user_id == user.id,
                    department_users.c.department_id == self.id
                ).first()
                
                if department_user and department_user.position_id:
                    position = Position.query.get(department_user.position_id)
                    if position:
                        user_position = position.to_dict()
                
                result['users'].append({
                    'user': user.to_dict(),
                    'position': user_position
                })
        return result 