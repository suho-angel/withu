docker compose build
docker compose up -d
# withu Backend (Flask)

안심귀가 앱 백엔드: 회원가입(이메일 코드 1회 검증), 사용자 프로필, 보호자(긴급 연락처) 관리.

## 주요 기술 스택
- Python / Flask
- SQLAlchemy (Flask-SQLAlchemy), Flask-Migrate (토이 모드에선 `db.create_all()`)
- MySQL (docker-compose)
- JWT (PyJWT)
- dotenv 환경변수 관리
- Gunicorn (WSGI 서버)

## 환경변수 (.env.example 참고)
```
SECRET_KEY=change_me_dev_secret
JWT_SECRET=change_me_jwt_secret
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DB=withu
MYSQL_USER=withu
MYSQL_PASSWORD=withu_pass

# SMTP (email verification - optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_account@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_USE_TLS=1
MAIL_FROM=no-reply@example.com
```
SMTP 미설정 시 이메일은 실제 전송 대신 서버 로그/콘솔 출력으로 대체되며 회원가입 응답에 `debug_verification_code`가 포함됩니다.
실제 운영에서는 반드시 실제 SMTP 설정을 적용하고 debug 코드 반환을 제거하세요.

## 설치 & 실행 (Docker 권장)
## API 명세서
상세한 엔드포인트, 요청/응답, 에러 규칙은 `docs/API_SPEC.md` 참조.

```bash
docker compose build
docker compose up -d
```

헬스 체크:
```bash
curl http://localhost:18888/health
```

Gunicorn 실행 (workers=3, threads=2, timeout=60). 환경변수 조정 가능:
```
GUNICORN_WORKERS=3
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=60
```

## 토이 모드 스키마 관리
마이그레이션을 생략하고 앱 시작 시 `db.create_all()`로 테이블 생성합니다.
모델 변경(컬럼 추가 등) 시 기존 테이블 자동 갱신되지 않으므로 필요하면 DB 볼륨 삭제(`docker compose down -v`) 후 재생성하세요.

## 주요 모델 개요
- User: 로그인 주체, 이메일·자동생성 username·비밀번호 해시 (가입 시점 = 이메일 인증 시점)
<!-- EmailVerification 및 RegistrationRequest 모델 제거: 세션 기반 코드 검증 완료 후 즉시 인증 -->
- Guardian: 보호자(관계, 이름, 전화번호) - 사용자별 다수, 전화번호 중복 방지
- UserProfile: 프로필(gender, name, birth_year, phone) - 사용자 1:1

## API 엔드포인트 요약
### Health
GET /health -> {"status": "ok"}
예시:
```bash
curl http://localhost:18888/health
```

### 회원가입 (이메일 코드 발송 후 최종 등록)
1) 인증코드 발송
POST /auth/send-code
Body JSON:
```
{
  "email": "user@example.com"
}
```
응답: 200 `{ message, expires_in_minutes: 15 }` (개발 환경에서는 `dev_code` 포함)
설명: 6자리 코드 이메일 발송 후 서버 DB에 저장하지 않고 세션(서명 쿠키)에만 `{email, code, expires_at}` 임시 저장. 가입 성공 시 바로 인증 완료 처리하며 추가 EmailVerification 레코드/테이블을 사용하지 않음.
주의: 다중 브라우저/디바이스에서는 각각 코드 발급 상태가 분리됨. 운영 환경에서 다중 서버/워커 확장을 고려하면 Redis 등 중앙 캐시 사용을 권장.

2) 최종 회원가입
POST /auth/register
Body JSON:
```
{
  "email": "user@example.com",
  "password": "secret123",
  "code": "123456"
}
```
응답: 201 + user (verified=true)
설명: 세션 내 저장된 코드/만료와 비교 후 User 생성 + 자동 username 할당. 성공 시 세션의 pending_registration 제거. 이메일 인증은 가입 시점으로 간주.

3) 로그인
POST /auth/login
Body JSON:
```
{
  "identity": "user@example.com",  # 이메일 또는 자동생성된 사용자명
  "password": "secret123"
}
```
실패: 401 (사용자 없음/비밀번호 불일치)
성공: 200 + JWT 토큰 (별도 이메일 미인증 상태 없음)

<!-- 과거 /auth/resend 엔드포인트는 제거되었습니다: send-code 재호출로 대체 -->

5) 회원탈퇴
DELETE /auth/delete (Bearer JWT 필요) → 관련 Guardian / Profile 레코드 함께 제거.

### 보호자(긴급 연락처) 관리
모든 엔드포인트 JWT 필요.

1) 목록 조회
GET /contacts → `{ "items": [ ... ] }`

2) 생성
POST /contacts
Body JSON:
```
{
  "relation": "엄마",   // 엄마|아빠|형제|친구|기타
  "name": "홍길동",
  "phone": "010-1234-5678"
}
```
응답: 201 + contact

3) 수정
PATCH /contacts/{id} (relation, name, phone 중 일부)
응답: 200 + contact

4) 삭제
DELETE /contacts/{id} → 200

### 사용자 프로필
JWT 필요. 회원가입과 독립적인 선택적 정보.

1) 조회
GET /profile → `{ "profile": null | { ... } }`

2) 생성/수정 (같은 엔드포인트)
POST /profile 또는 PATCH /profile
Body JSON(필드 일부만 가능):
```
{
  "gender": "남",      // 남|여|기타 (optional)
  "name": "홍길동",    // optional
  "birth_year": 1995,  // 1900~현재 연도
  "phone": "010-9999-8888" // 형식 검증(+ 숫자 - 공백)
}
```
응답: 생성 201 / 수정 200 + profile

### 오류 코드 요약 (회원가입 관련)
| 상황 | 상태코드 | 메시지 (예시) |
|------|---------|----------------|
| 필수 필드 누락(register) | 400 | email, password 필요 |
| 비밀번호 6자 미만 | 400 | 비밀번호는 6자 이상 |
| 진행중/기존 이메일 존재 | 409 | 이미 존재하거나 진행중인 이메일 |
| 가입 요청 없음 (verify) | 404 | 진행중인 가입 요청 없음 |
| 코드 불일치 | 400 | 코드 불일치 |
| 코드 만료 | 400 | 코드 만료 |
| 보호자 중복(phone) | 409 | 이미 등록된 전화번호 |
| 보호자 없음 | 404 | 해당 보호자를 찾을 수 없음 |
| 프로필 gender 잘못됨 | 400 | gender는 [남,여,기타] 중 하나여야 함 |

## 회원가입/인증 테스트 방법 (토이 모드)
실제 SMTP 사용 시 이메일 수신 후 코드 확인 → /auth/verify.

토이 환경에서 빠른 테스트를 위해 두 가지 방법 중 선택:
<!-- 과거 RegistrationRequest 코드를 직접 조회하던 예시는 폐기되었습니다. -->
2) 개발 로그 출력(옵션): `send_email` 함수 내에서 SMTP 미설정 시 콘솔에 코드 출력. 실제 운영 시 제거 필수.

권장: 운영/스테이징에서는 반드시 실제 이메일 흐름 검증. 테스트용 코드 노출은 로컬 개발 환경에만 제한.

## 후속 개선 아이디어
- Refresh Token & 만료 관리
- 패스워드 정책 강화 / 이메일 검증 개선 (복수 코드/재발송 제한)
- 로깅 & 모니터링 (구조적 로그)
- 유닛 테스트 (pytest) 추가
- Rate Limiting (Flask-Limiter)
- Gunicorn worker class 변경 (gevent/eventlet) 또는 ASGI 전환 (uvicorn + FastAPI/Quart)
- 이메일 템플릿/HTML 메일
- 통합 응답 포맷(success/error wrapper)
- Guardian 최대 개수 제한 및 SMS Opt-in 필드
- 프로필 필드 필수화 정책(초기 가입 후 N시간 내 작성)

## WSGI 서버 선택 참고
- Gunicorn: 간단/표준
- uWSGI: 고성능/복잡한 설정
- Waitress: Windows 호환/단순
- Hypercorn/uvicorn: ASGI (비동기 필요 시)

workers 수는 일반적으로 `(2 * 코어) + 1` 권장값을 기준으로 조정.

## 라이선스
사내/개인 프로젝트 목적.
