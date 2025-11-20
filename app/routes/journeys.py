from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.user import User
from app.models.journey_event import JourneyEvent, ALLOWED_JOURNEY_TYPES
import jwt

bp = Blueprint('journeys', __name__, url_prefix='/journeys')


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


@bp.route('/start', methods=['POST'])
def start_journey():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    ev = JourneyEvent(user_id=user.id, event_type='출발')
    db.session.add(ev)
    db.session.commit()
    return jsonify({'message': '출발이 기록되었습니다', 'event': ev.to_dict()}), 201


@bp.route('/arrive', methods=['POST'])
def arrive_journey():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    ev = JourneyEvent(user_id=user.id, event_type='도착')
    db.session.add(ev)
    db.session.commit()
    return jsonify({'message': '도착이 기록되었습니다', 'event': ev.to_dict()}), 201


@bp.route('', methods=['GET'])
def list_journeys():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code
    try:
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))
    items = [e.to_dict() for e in JourneyEvent.query.filter_by(user_id=user.id).order_by(JourneyEvent.id.desc()).limit(limit).all()]
    return jsonify({'items': items}), 200
