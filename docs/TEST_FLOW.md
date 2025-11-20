# End-to-End Flow Test (withu)

본 문서는 전체 기능 시나리오를 자동으로 검증하는 스크립트(`scripts/test_flow.sh`) 사용 방법을 설명합니다.

## 목적
가입 → 로그인 → 프로필 생성 → 보호자 등록 → 위험 알림 기록 → 여정 출발/도착 → 조회 → 회원탈퇴 → 재로그인 실패 여부까지 전체 수명주기 검증.

## 선행 조건
- 서버가 로컬에서 실행 중이어야 함: http://localhost:18888 (Gunicorn 혹은 flask dev)
- 개발 모드(환경 변수 `ENV=development`)에서 실행되어야 `send-code` 응답에 `dev_code` 필드 노출됨.
- `curl`, `jq` 설치 필요 (macOS: `brew install curl jq`).

## 실행 방법
```bash
chmod +x scripts/test_flow.sh
./scripts/test_flow.sh
```
스크립트는 타임스탬프가 포함된 고유 이메일을 생성하므로 매 실행마다 중복 없이 진행됩니다.

## 검증 항목
1. `/auth/send-code` 호출 및 dev_code 확보
2. `/auth/register` 정상 가입 및 User ID/username 추출
3. `/auth/login` JWT 토큰 획득
4. `/profile` 프로필 최초 생성 (201 vs 200 구분은 스크립트에서 메시지 검사)
5. `/contacts` 보호자 등록 및 ID 추출
6. `/alerts/notify` 위험 알림 기록 및 이벤트 ID 추출
7. `/journeys/start` 출발 이벤트 기록
8. `/journeys/arrive` 도착 이벤트 기록
9. `/alerts` & `/journeys` 목록 조회 (최소 개수 확인)
10. `/auth/delete` 회원탈퇴 처리
11. 탈퇴 후 `/auth/login` 재시도 실패 확인

## 실패 처리 기준
- 각 단계별 필수 필드/메시지 누락 시 즉시 스크립트 종료 및 오류 출력.
- 재로그인 단계는 실패가 정상이며, 실패하지 않을 경우 경고 표시.

## 출력 예시
마지막에 요약 블록과 "전체 플로우 PASS" 녹색 메시지를 표시.

## 확장 아이디어
- GitHub Actions 에서 cron 으로 주기적 실행 → 기본 가용성 검증
- Rate limiting 모듈 적용 후 429 케이스 추가 검증
- SMS 실제 발송 기능 연동 시 Mock 계층 도입
- 프로필 수정/보호자 업데이트/삭제 추가 시나리오 분기

## 문제 해결 가이드
- dev_code 미노출: 환경 변수 `ENV=development` 설정 여부 확인
- 로그인 401: 비밀번호 정책 위반 또는 토큰 서명 키(`JWT_SECRET`) 불일치
- DB 무결성 오류: 이전 테스트 잔존 데이터 확인 (고유 제약 조건 충돌)

## 제거 고려 사항 (향후)
회원탈퇴 시 AlertLog/JourneyEvent 정리(익명화 또는 삭제) 정책 확정 후 스크립트 수정 필요.

---
문서 버전: 0.1.0
