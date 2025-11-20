from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.guardian import Guardian, ALLOWED_RELATIONS
from app.models.user import User
import jwt

bp = Blueprint('contacts', __name__, url_prefix='/contacts')


def _get_auth_token():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1].strip()


def _current_user_from_jwt():
    token = _get_auth_token()
    if not token:
        return None, ('인증 토큰 누락 또는 형식 오류', 401)
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None, ('토큰 만료', 401)
    except jwt.InvalidTokenError:
        return None, ('토큰 검증 실패', 401)
    user = User.query.get(payload.get('sub'))
    if not user:
        return None, ('사용자 없음', 404)
    return user, None


def _validate_phone(phone: str) -> bool:
    if not phone or not isinstance(phone, str):
        return False
    # 간단 검증: +, 숫자, -, 공백 허용 / 길이 8~20
    allowed = set("0123456789+ -")
    if not set(phone) <= allowed:
        return False
    digits = [c for c in phone if c.isdigit()]
    return 8 <= len(digits) <= 20


@bp.route('', methods=['GET'])
def list_contacts():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    items = [c.to_dict() for c in user.contacts.order_by(Guardian.id.asc()).all()]
    return jsonify({'items': items}), 200


@bp.route('', methods=['POST'])
def create_contact():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    data = request.get_json(silent=True) or {}
    relation = data.get('relation')
    name = data.get('name')
    phone = data.get('phone')

    if not all([relation, name, phone]):
        return jsonify({'error': 'relation, name, phone 필요'}), 400
    if relation not in ALLOWED_RELATIONS:
        return jsonify({'error': f"relation은 {sorted(list(ALLOWED_RELATIONS))} 중 하나여야 함"}), 400
    if not _validate_phone(phone):
        return jsonify({'error': '유효하지 않은 전화번호 형식'}), 400

    # 중복(phone) 체크
    exists = Guardian.query.filter_by(user_id=user.id, phone=phone).first()
    if exists:
        return jsonify({'error': '이미 등록된 전화번호'}), 409

    g = Guardian(user_id=user.id, relation=relation, name=name, phone=phone)
    db.session.add(g)
    db.session.commit()
    return jsonify({'message': '보호자 등록 완료', 'contact': g.to_dict()}), 201


@bp.route('/<int:contact_id>', methods=['PUT', 'PATCH'])
def update_contact(contact_id):
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    g = Guardian.query.filter_by(id=contact_id, user_id=user.id).first()
    if not g:
        return jsonify({'error': '해당 보호자를 찾을 수 없음'}), 404

    data = request.get_json(silent=True) or {}
    relation = data.get('relation')
    name = data.get('name')
    phone = data.get('phone')

    if relation is not None:
        if relation not in ALLOWED_RELATIONS:
            return jsonify({'error': f"relation은 {sorted(list(ALLOWED_RELATIONS))} 중 하나여야 함"}), 400
        g.relation = relation
    if name is not None:
        if not name:
            return jsonify({'error': 'name은 비어있을 수 없음'}), 400
        g.name = name
    if phone is not None:
        if not _validate_phone(phone):
            return jsonify({'error': '유효하지 않은 전화번호 형식'}), 400
        # 다른 연락처와 중복 방지
        dup = Guardian.query.filter(Guardian.user_id == user.id, Guardian.phone == phone, Guardian.id != g.id).first()
        if dup:
            return jsonify({'error': '다른 보호자에 동일 전화번호가 존재'}), 409
        g.phone = phone

    db.session.commit()
    return jsonify({'message': '보호자 수정 완료', 'contact': g.to_dict()}), 200


@bp.route('/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    g = Guardian.query.filter_by(id=contact_id, user_id=user.id).first()
    if not g:
        return jsonify({'error': '해당 보호자를 찾을 수 없음'}), 404

    db.session.delete(g)
    db.session.commit()
    return jsonify({'message': '보호자 삭제 완료'}), 200
