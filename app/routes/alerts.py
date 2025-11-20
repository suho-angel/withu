from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models.user import User
from app.models.guardian import Guardian
from app.models.alert_log import AlertLog, ALLOWED_ALERT_REASONS
import jwt

bp = Blueprint('alerts', __name__, url_prefix='/alerts')


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


@bp.route('/notify', methods=['POST'])
def notify_guardians():
    """위험 감지 시 보호자에게 연락 요청 이력을 기록.
    Body: { reason: '경로이탈' | '위험음 감지' | '도착 지연' }
    실제 SMS 발송은 아직 없음 (추후 연동 예정).
    """
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    if reason not in ALLOWED_ALERT_REASONS:
        return jsonify({'error': f"reason은 {sorted(list(ALLOWED_ALERT_REASONS))} 중 하나여야 함"}), 400

    guardians = user.contacts.order_by(Guardian.id.asc()).all()
    recipients = [
        {'relation': g.relation, 'name': g.name, 'phone': g.phone}
        for g in guardians
    ]

    log = AlertLog(user_id=user.id, reason=reason, recipients=recipients)
    db.session.add(log)
    db.session.commit()

    # TODO: 추후 SMS/푸시 연동 시 여기에서 비동기 큐 작업 enqueue
    return jsonify({'message': '보호자 연락 요청이 기록되었습니다', 'event': log.to_dict()}), 201


@bp.route('', methods=['GET'])
def list_alerts():
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    try:
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    logs = AlertLog.query.filter_by(user_id=user.id).order_by(AlertLog.id.desc()).limit(limit).all()
    items = [l.to_dict() for l in logs]
    return jsonify({'items': items}), 200
