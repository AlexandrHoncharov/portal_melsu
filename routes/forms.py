import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import db, User, Form

forms = Blueprint('forms', __name__)

@forms.route('', methods=['GET'])
@jwt_required()
def get_forms():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if 'admin' not in [role.name for role in user.roles]:
        return jsonify({'error': 'Недостаточно прав'}), 403

    forms = Form.query.order_by(Form.created_at.desc()).all()
    forms_data = []
    for form in forms:
        try:
            fields = json.loads(form.fields) if form.fields else []
        except json.JSONDecodeError:
            fields = []

        forms_data.append({
            'id': form.id,
            'name': form.name,
            'description': form.description,
            'type': form.form_type,
            'responsible': form.responsible,
            'period': form.period,
            'fields': fields,
            'create': form.created_at.isoformat() + 'Z',
            'status': 'Активна'
        })
    return jsonify(forms_data), 200

@forms.route('', methods=['POST'])
@jwt_required()
def create_form():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    try:
        form = Form(
            name=data.get('name'),
            description=data.get('description'),
            form_type=data.get('type'),
            responsible=data.get('responsible'),
            period=data.get('period'),
            fields=json.dumps(data.get('fields', [])),
            created_by=current_user_id
        )
        db.session.add(form)
        db.session.commit()

        return jsonify({
            'id': form.id,
            'message': 'Форма создана'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка создания формы'}), 500

@forms.route('/<int:form_id>', methods=['DELETE'])
@jwt_required()
def delete_form(form_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    user_roles = [role.name for role in user.roles]
    if 'admin' not in user_roles:
        return jsonify({'error': 'Недостаточно прав'}), 403

    form = Form.query.get(form_id)
    if not form:
        return jsonify({'error': 'Форма не найдена'}), 404

    try:
        db.session.delete(form)
        db.session.commit()
        return jsonify({'message': 'Форма удалена'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка удаления формы'}), 500 