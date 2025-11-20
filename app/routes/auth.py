from flask import Blueprint, request, jsonify, current_app, session
from app.extensions import db
from app.models.user import User
from app.utils.email import send_email
import jwt, os
from datetime import datetime, timedelta

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/send-code', methods=['POST'])
def send_code():
    """회원가입 전 이메일 인증코드 발송 (15분 유효). 서버 영속 저장 없이 세션에만 임시 보관.
    Body: { email: ... }
    Response: 200 { message, expires_in_minutes }
    주의: 다중 Gunicorn worker 환경에서는 세션(서명 쿠키)만 사용하므로 코드 검증 흐름은 문제 없지만
          서버 측 글로벌 메모리를 사용하지 않음. 동일 브라우저 세션 내에서만 유효.
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    if not email:
        return jsonify({'error': 'email 필요'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 존재하는 이메일'}), 409
    # 코드 생성 (평문 유지 - 세션은 서명되어 변경 시 무효)
    import secrets
    raw_code = ''.join(secrets.choice('0123456789') for _ in range(6))
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    session['pending_registration'] = {
        'email': email,
        'code': raw_code,
        'expires_at': expires_at.isoformat()
    }
    email_body = f"withu 회원가입 인증 코드: {raw_code}\n15분 내 회원가입을 완료하세요."
    send_email(email, "withu 이메일 인증", email_body)
    resp = {'message': '인증코드 발송 완료', 'expires_in_minutes': 15}
    # 개발 환경에서만 dev_code 반환 (ENV=development 판별)
    if current_app.config.get('ENV') == 'development':
        resp['dev_code'] = raw_code
    return jsonify(resp), 200

@bp.route('/register', methods=['POST'])
def register():
    """최종 회원가입 처리: email + password + code (세션 저장 기반).
    세션에 저장된 pending_registration 정보와 비교 후 User 생성.
    Body: { email, password, code }
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    code = data.get('code')
    if not all([email, password, code]):
        return jsonify({'error': 'email, password, code 필요'}), 400
    if len(password) < 6:
        return jsonify({'error': '비밀번호는 6자 이상'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 존재하는 이메일'}), 409
    pending = session.get('pending_registration')
    if not pending or pending.get('email') != email:
        return jsonify({'error': '인증코드 발급 상태 없음 (send-code 먼저 수행)'}), 404
    # 만료 확인
    try:
        expires_at = datetime.fromisoformat(pending.get('expires_at'))
    except Exception:
        return jsonify({'error': '세션 데이터 손상'}), 400
    if expires_at < datetime.utcnow():
        session.pop('pending_registration', None)
        return jsonify({'error': '코드 만료'}), 400
    if pending.get('code') != code:
        return jsonify({'error': '코드 불일치'}), 400

    # 자동 username 생성
    local_part = email.split('@')[0].lower()
    base = ''.join(ch if ch.isalnum() else '_' for ch in local_part) or 'user'
    candidate = base[:32]
    suffix = 1
    while User.query.filter_by(username=candidate).first():
        candidate = f"{base[:28]}_{suffix}"
        suffix += 1
        if suffix > 9999:
            break

    user = User(email=email, username=candidate)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    # EmailVerification 테이블 제거: 가입 완료 시점 즉시 인증 처리
    db.session.commit()
    session.pop('pending_registration', None)
    return jsonify({'message': '회원가입 및 이메일 인증 완료', 'user': user.to_dict()}), 201

# 기존 /verify, /resend 흐름 제거 -> resend는 send-code 재호출로 대체

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email_or_username = data.get('identity')  # email 또는 username 허용
    password = data.get('password')

    if not all([email_or_username, password]):
        return jsonify({'error': 'identity, password 필요'}), 400

    user = User.query.filter((User.email == email_or_username) | (User.username == email_or_username)).first()
    if not user or not user.check_password(password):
        return jsonify({'error': '인증 실패'}), 401

    # EmailVerification 제거 후 모든 가입 사용자는 즉시 인증된 것으로 간주
    payload = {
        'sub': user.id,
        'exp': datetime.utcnow() + timedelta(hours=12),
        'iat': datetime.utcnow(),
        'username': user.username
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    return jsonify({'message': '로그인 성공', 'token': token, 'user': user.to_dict()}), 200


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

@bp.route('/delete', methods=['DELETE'])
def delete_account():
    """JWT 인증된 사용자의 계정을 삭제.
    처리:
    - 관련 EmailVerification 레코드 먼저 제거
    - User 레코드 삭제
    - 커밋 후 200 반환
    보안:
    - Bearer 토큰 필요
    """
    user, error = _current_user_from_jwt()
    if error:
        msg, code = error
        return jsonify({'error': msg}), code

    # EmailVerification 관계 제거됨. 관련 보호자 레코드 삭제
    # 프로필 및 보호자 명시적 삭제 (cascade 보강 + 안전성)
    from app.models.alert_log import AlertLog
    from app.models.journey_event import JourneyEvent
    try:
        if user.profile:
            db.session.delete(user.profile)
    except Exception:
        pass
    try:
        guardians = user.contacts.all()
    except Exception:
        guardians = []
    for g in guardians:
        db.session.delete(g)
    # 관련 이벤트/알림 로그 일괄 삭제 (FK cascade 미적용 환경 대비)
    AlertLog.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    JourneyEvent.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'삭제 실패: {str(e)}'}), 500
    return jsonify({'message': '회원탈퇴 완료', 'user_id': user.id}), 200
