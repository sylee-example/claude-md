---
description: AS-IS 화면(JSP) 1개 분석 → 화면 명세서 작성 (코드 생성 없음)
argument-hint: <AS-IS .jsp> [관련 js 파일...]
allowed-tools: Bash(python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" *)
disallowed-tools: Edit
disable-model-invocation: true
---
!`python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" spec-screen $ARGUMENTS`

---

# 지시

작업지시서가 "# 작업지시서 생성 실패" 로 시작하면 아래는 무시하고, 그 메시지만 사용자에게 보고하고 끝낸다.

코드를 만들지 않는다. 위 화면(과 첨부 js)을 분석해서 아래 양식을 그대로 채워 "명세 저장 경로" 에 Write 한다.

- 필드명은 TO-BE camel ("2. 매핑" 표의 TO-BE 필드). AS-IS 이름은 "AS-IS" 열에만 쓴다.
- 모르는 것은 추측하지 말고 `TODO(HARNESS): 사유`.
- 양식의 제목·표 머리글·"상태" 줄은 바꾸지 않는다.

````markdown
# 화면 명세: <화면명>

- AS-IS: `$0`
- 상태: 검토 전   ← 사람이 검토 후 "검토 완료"로 바꾼다
- 라우트: (예: /customer/list)
- 엔티티: (예: customer)
- 화면 슬러그: (예: customer-list)

## 1. 조회 조건
| 필드(TO-BE camel) | 라벨 | 컴포넌트 (Input/Select/DatePicker/...) | 필수 | 기본값 | 공통코드 | AS-IS |
|---|---|---|---|---|---|---|

## 2. 그리드
| field(TO-BE camel) | headerName | 타입 (text/number/date/code) | 폭 | 편집 | 포맷 | AS-IS |
|---|---|---|---|---|---|---|

## 3. 버튼·이벤트
| 버튼/이벤트 | 동작 | 호출 API | 성공 후 처리 |
|---|---|---|---|

## 4. API
| 이름 | HTTP | URL | 요청 필드 | 응답 필드 | AS-IS 호출 (거래 ID / URL) |
|---|---|---|---|---|---|

## 5. 팝업·화면 이동

## 6. 권한·특이사항

## 7. TODO(HARNESS)
````

끝나면 CLAUDE.md 의 "변환 보고" 형식으로만 답한다.
