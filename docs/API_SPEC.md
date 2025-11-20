# withu API 명세서

버전: 0.1.1 (토이 모드)  
최종 갱신: 2025-11-19

## 공통 개념
- Base URL: `http://localhost:18888`
- 모든 요청/응답은 JSON (UTF-8)
- 인증: 일부 엔드포인트는 Bearer JWT 토큰 필요 (`Authorization: Bearer <token>`)
- 개발 모드(ENV=development)에서만 회원가입 코드 응답에 `dev_code` 포함
- 세션: 이메일 인증 코드 발급(`send-code`) 시 브라우저 쿠키 기반 세션에 `pending_registration` 저장
- 이메일 인증: 가입 시점 = 인증 시점 (추가 EmailVerification 테이블 없음)

## 인증 및 보안
### JWT 토큰
- 발급: `/auth/login` 성공 응답의 `token`
- 내용: `{ sub: <user_id>, exp: <만료UTC>, iat: <발급UTC>, username: <사용자명> }`
- 알고리즘: HS256, 시크릿: `JWT_SECRET`
- 만료: 현재 12시간 (로그인 시점 기준)

### 에러 응답 포맷
```json
{ "error": "메시지" }
```
추가 필드가 필요한 경우(예: verified 등) 확장될 수 있음.

## 상태 코드 일반 규칙
| 상황 | 코드 |
|------|------|
| 성공 조회 | 200 |
| 생성 | 201 |
| 잘못된 입력 | 400 |
| 인증/인가 실패 | 401 / 403 |
| 리소스 없음 | 404 |
| 충돌(중복 등) | 409 |
| 서버 오류 | 500 |

---
## Health
### GET /health
- 설명: 서버 동작 여부 확인
- 인증: 불필요
- 응답 200:
```json
{ "status": "ok" }
```

---
## 회원가입 / 인증 관련 (Auth)
### 1. POST /auth/send-code
- 설명: 이메일 인증 코드(6자리) 발송, 세션에 저장
- 바디:
```json
{ "email": "user@example.com" }
```
- 응답 200 (dev 환경):
```json
{ "message": "인증코드 발송 완료", "expires_in_minutes": 15, "dev_code": "123456" }
```
- 응답 200 (prod 환경):
```json
{ "message": "인증코드 발송 완료", "expires_in_minutes": 15 }
```
- 에러:
  - 400: email 누락
  - 409: 이미 존재하는 이메일

### 2. POST /auth/register
- 설명: 세션에 저장된 코드 검증 후 사용자 생성
- 바디:
```json
{ "email": "user@example.com", "password": "Pass1234", "code": "123456" }
```
- 응답 201:
```json
{
  "message": "회원가입 및 이메일 인증 완료",
  "user": {
    "id": 7,
    "email": "user@example.com",
    "username": "user",
    "verified": true,
    "created_at": "2025-11-19T00:00:00",
    "updated_at": "2025-11-19T00:00:00"
  }
}
```
- 에러:
  - 400: 필수 필드 누락 / 비밀번호 짧음 / 코드 만료 / 코드 불일치 / 세션 손상
  - 404: 코드 발급 상태 없음
  - 409: 이미 존재하는 이메일

### 3. POST /auth/login
- 설명: 이메일 또는 username 으로 로그인(JWT 발급)
- 바디:
```json
{ "identity": "user@example.com", "password": "Pass1234" }
```
- 응답 200:
```json
{
  "message": "로그인 성공",
  "token": "<JWT>",
  "user": {
    "id": 7,
    "email": "user@example.com",
    "username": "user",
    "verified": true,
    "created_at": "...",
    "updated_at": "..."
  }
}
```
- 에러:
  - 400: 필드 누락
  - 401: 인증 실패(사용자 없음 또는 비밀번호 불일치)

### 4. DELETE /auth/delete
- 설명: 인증된 사용자 계정 삭제(Guardian, Profile 함께 제거)
- 헤더: `Authorization: Bearer <JWT>`
- 응답 200:
```json
{ "message": "회원탈퇴 완료", "user_id": 7 }
```
- 에러:
  - 401: 토큰 누락/형식 오류/만료/검증 실패
  - 404: 사용자 없음
  - 500: 삭제 실패

---
## 사용자 프로필 (Profile)
### GET /profile
- 설명: 현재 사용자 프로필 조회
- 헤더: `Authorization: Bearer <JWT>`
- 응답 200 (없음):
```json
{ "profile": null }
```
- 응답 200 (있음):
```json
{ "profile": { "gender": "여", "name": "홍길동", "birth_year": 1995, "phone": "010-1234-5678", "created_at": "...", "updated_at": "..." } }
```
- 에러: 401 / 404 (사용자 없음)

### POST /profile (또는 PATCH /profile)
- 설명: 최초 생성 또는 수정(같은 엔드포인트)
- 바디 (필드 일부만 전송 가능):
```json
{ "gender": "남", "name": "홍길동", "birth_year": 1990, "phone": "+82 10 1234 5678" }
```
- 응답 201(생성) 또는 200(수정):
```json
{ "message": "프로필 생성", "profile": { ... } }
```
- 검증:
  - gender: 남|여|기타 중 하나
  - birth_year: 1900 ~ 현재 연도
  - phone: 허용 문자(+ 숫자 - 공백) 총 숫자 8~20자리
- 에러: 400(검증 실패), 401/404(인증/사용자 없음)

---
## 보호자 관리 (Contacts / Guardians)
### GET /contacts
- 설명: 사용자 보호자 목록 조회
- 헤더: `Authorization: Bearer <JWT>`
- 응답 200:
```json
{ "items": [ { "id": 1, "relation": "엄마", "name": "Kim Mother", "phone": "010-1234-5678", "created_at": "...", "updated_at": "..." } ] }
```

### POST /contacts
- 설명: 보호자 추가
- 바디:
```json
{ "relation": "엄마", "name": "Kim Mother", "phone": "010-1234-5678" }
```
- relation 허용값: 엄마|아빠|형제|친구|기타
- 응답 201:
```json
{ "message": "보호자 등록 완료", "contact": { ... } }
```
- 에러:
  - 400: 필드 누락/형식 오류
  - 409: 동일 전화번호 이미 존재

### PATCH /contacts/{id} (또는 PUT)
- 설명: 보호자 정보 수정(일부 필드만 갱신 가능)
- 바디 예:
```json
{ "phone": "010-9999-8888" }
```
- 응답 200:
```json
{ "message": "보호자 수정 완료", "contact": { ... } }
```
- 에러:
  - 400: 검증 실패
  - 404: 보호자 없음
  - 409: 다른 보호자와 전화번호 충돌

### DELETE /contacts/{id}
- 설명: 보호자 삭제
- 응답 200:
```json
{ "message": "보호자 삭제 완료" }
```
- 에러: 404 보호자 없음

---
## 자동신고 / 위험 알림 (Alerts)
### POST /alerts/notify
- 설명: 위험 사유 발생 시 보호자에게 연락 요청 이력 기록 (실제 SMS 미발송, 추후 연동)
- 바디:
```json
{ "reason": "경로이탈" }
```
- reason 허용값: 경로이탈 | 위험음 감지 | 도착 지연
- 응답 201:
```json
{
  "message": "보호자 연락 요청이 기록되었습니다",
  "event": {
    "id": 10,
    "user_id": 7,
    "reason": "경로이탈",
    "recipients": [ { "relation": "엄마", "name": "Kim Mother", "phone": "+82 10 8888 9999" } ],
    "recipients_count": 1,
    "created_at": "..."
  }
}
```
- 에러:
  - 400: reason 잘못됨
  - 401/404: 인증/사용자 없음

### GET /alerts?limit=50
- 설명: 최신 위험 알림 이력 조회 (limit 기본 50, 최대 200)
- 응답 200:
```json
{ "items": [ { "id": 10, "user_id": 7, "reason": "경로이탈", "recipients": [...], "recipients_count": 1, "created_at": "..." } ] }
```

---
## 여정 기록 (Journeys)
출발/도착은 단순 기록/조회용입니다. 보호자 연락은 수행하지 않습니다.

### POST /journeys/start
- 설명: 출발 이벤트 기록
- 헤더: `Authorization: Bearer <JWT>`
- 응답 201:
```json
{ "message": "출발이 기록되었습니다", "event": { "id": 1, "user_id": 7, "event_type": "출발", "created_at": "..." } }
```

### POST /journeys/arrive
- 설명: 도착 이벤트 기록
- 헤더: `Authorization: Bearer <JWT>`
- 응답 201:
```json
{ "message": "도착이 기록되었습니다", "event": { "id": 2, "user_id": 7, "event_type": "도착", "created_at": "..." } }
```

### GET /journeys?limit=50
- 설명: 최신 여정 이벤트(출발/도착) 목록 조회 (limit 기본 50, 최대 200)
- 헤더: `Authorization: Bearer <JWT>`
- 응답 200:
```json
{ "items": [ { "id": 2, "user_id": 7, "event_type": "도착", "created_at": "..." }, { "id": 1, "user_id": 7, "event_type": "출발", "created_at": "..." } ] }
```

---
## 데이터 모델 요약 (단순화 버전)
### User
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| email | string(255) | 고유 이메일 |
| username | string(64) | 자동 생성 사용자명 |
| password_hash | string | 비밀번호 해시 (scrypt) |
| created_at | datetime | 생성 시각 |
| updated_at | datetime | 수정 시각 |
| verified | (to_dict 가공) | 항상 true (가입=인증) |

### UserProfile
| 필드 | 타입 | 설명 |
| id | int | PK |
| user_id | int | FK(User) |
| gender | string(8) | 남/여/기타 또는 null |
| name | string(64) | 이름(optional) |
| birth_year | int | 출생연도(optional) |
| phone | string(32) | 전화(optional) |
| created_at | datetime | 생성 |
| updated_at | datetime | 수정 |

### Guardian
| 필드 | 타입 | 설명 |
| id | int | PK |
| user_id | int | FK(User) |
| relation | string(16) | 엄마/아빠/형제/친구/기타 |
| name | string(64) | 보호자 이름 |
| phone | string(32) | 전화 (사용자 내 중복 금지) |
| created_at | datetime | 생성 |
| updated_at | datetime | 수정 |

### AlertLog
| 필드 | 타입 | 설명 |
| id | int | PK |
| user_id | int | FK(User) |
| reason | string(32) | 경로이탈/위험음 감지/도착 지연 |
| recipients | JSON | 당시 보호자 스냅샷 배열 [{relation,name,phone}] |
| created_at | datetime | 생성 시각 |

### JourneyEvent
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| user_id | int | FK(User) |
| event_type | string(16) | 출발/도착 |
| created_at | datetime | 생성 시각 |

---
## 확장/향후 고려 사항
| 항목 | 설명 |
|------|------|
| Rate Limiting | send-code / alerts/notify 남용 방지 (IP + 사용자) |
| SMS/푸시 연동 | alerts/notify 후 비동기 큐 처리(SQS, Redis, Celery 등) |
| 재인증 흐름 | 이메일 변경 시 추가 코드 검증 필요 시 별 Request 테이블 도입 |
| 표준 응답 포맷 | `{ success: true/false, data: ..., error: { code, message } }` 채택 가능 |
| 테스트 자동화 | pytest로 엔드투엔드/단위 테스트 구축 |
| 보안 강화 | 비밀번호 정책, 브루트포스 방지, JWT refresh token, HTTPS 적용 |

## 예시 시나리오 흐름
1. `POST /auth/send-code` → dev_code 확인 (로컬)
2. `POST /auth/register` (email/password/code)
3. `POST /auth/login` → JWT 획득
4. `POST /profile` → 프로필 등록
5. `POST /contacts` → 보호자 등록
6. 위험 발생 → `POST /alerts/notify` (reason)
7. `GET /alerts` 로 이력 조회
8. `POST /journeys/start` → 출발 기록
9. `POST /journeys/arrive` → 도착 기록
10. `GET /journeys` → 여정 이벤트 조회

## 버전 관리
- v0.1.0: 초기 핵심(회원가입, 프로필, 보호자, 위험 알림) 완료 / 이메일 인증 단순화.

---
## 변경 로그 (요약)
- 제거: EmailVerification, RegistrationRequest (세션 기반 즉시 인증)
- 추가: AlertLog (위험 알림 기록), JourneyEvent(출발/도착 기록)
- 단순화: 가입 시 verified 항상 true

---
## 라이선스 / 저작권
사내/개인 프로젝트 용도. 외부 배포 전 별도 라이선스 명시 필요.
