from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.user import User
from app.models.user_profile import UserProfile, ALLOWED_GENDERS
import jwt
from datetime import datetime

bp = Blueprint('profile', __name__, url_prefix='/profile')


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
    if phone is None:
        return True  # optional
    allowed = set("0123456789+ -")
    if not set(phone) <= allowed:
        return False
    digits = [c for c in phone if c.isdigit()]
    return 8 <= len(digits) <= 20


def _validate_birth_year(by):
    if by is None:
        return True
    try:
        year = int(by)
    except (TypeError, ValueError):
        return False
    current_year = datetime.utcnow().year
    return 1900 <= year <= current_year

@bp.route('', methods=['GET'])
def get_profile():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    if not user.profile:
        return jsonify({'profile': None}), 200
    return jsonify({'profile': user.profile.to_dict()}), 200

@bp.route('', methods=['POST', 'PATCH'])
def upsert_profile():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    data = request.get_json(silent=True) or {}
    gender = data.get('gender')
    name = data.get('name')
    birth_year = data.get('birth_year')
    phone = data.get('phone')

    if gender is not None and gender not in ALLOWED_GENDERS:
        return jsonify({'error': f"gender는 {sorted(list(ALLOWED_GENDERS))} 중 하나여야 함"}), 400
    if birth_year is not None and not _validate_birth_year(birth_year):
        return jsonify({'error': '유효하지 않은 birth_year'}), 400
    if phone is not None and not _validate_phone(phone):
        return jsonify({'error': '유효하지 않은 phone 형식'}), 400

    profile = user.profile
    created = False
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        created = True

    if gender is not None:
        profile.gender = gender
    if name is not None:
        profile.name = name
    if birth_year is not None:
        profile.birth_year = int(birth_year)
    if phone is not None:
        profile.phone = phone

    db.session.commit()
    return jsonify({'message': '프로필 생성' if created else '프로필 수정', 'profile': profile.to_dict()}), (201 if created else 200)
