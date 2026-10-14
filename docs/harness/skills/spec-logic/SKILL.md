---
description: AS-IS 로직(메서드) 1개 분석 → 로직 명세서 작성 (코드 생성 없음)
argument-hint: <AS-IS .java> <메서드명>
allowed-tools: Bash(python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" *)
disallowed-tools: Edit
disable-model-invocation: true
---
!`python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" spec-logic $ARGUMENTS`

---

# 지시

작업지시서가 "# 작업지시서 생성 실패" 로 시작하면 아래는 무시하고, 그 메시지만 사용자에게 보고하고 끝낸다.

코드를 만들지 않는다. 위 메서드를 분석해서 아래 양식을 그대로 채워 "명세 저장 경로" 에 Write 한다.

- 모든 이름은 TO-BE 이름 ("2. 매핑" 표 기준). AS-IS 이름은 "AS-IS 이름" 열에만 쓴다.
- 모르는 것은 추측하지 말고 `TODO(HARNESS): 사유`.
- 양식의 제목·표 머리글·"상태" 줄은 바꾸지 않는다.

````markdown
# 로직 명세: <TO-BE 서비스 메서드명>

- AS-IS: `$0` / `$1`
- 상태: 검토 전   ← 사람이 검토 후 "검토 완료"로 바꾼다

## 0. 생성 파일 (표준 예시의 경로 규칙을 따른다)
| 종류 | 경로 | 클래스.메서드 |
|---|---|---|
| Controller | | |
| Service | | |
| 요청 DTO | | |
| 응답 DTO | | |
| Mapper 인터페이스 | | |

## 1. 입력 (요청 DTO)
| 필드(TO-BE camel) | 타입 | 필수 | AS-IS 이름 | 설명 |
|---|---|---|---|---|

## 2. 출력 (응답 DTO)
| 필드(TO-BE camel) | 타입 | AS-IS 이름 | 설명 |
|---|---|---|---|

## 3. 처리 순서
1. (한 줄에 한 동작. 분기는 "만약 ~ 이면 ~")

## 4. 호출하는 쿼리
| statement id | 종류 (select/insert/update/delete) | 용도 |
|---|---|---|

## 5. 호출하는 SAP RFC
| RFC 함수 | RAP 경로 (매핑 표) | 용도 |
|---|---|---|

## 6. 트랜잭션
조회 전용 / 저장 포함 (근거 한 줄)

## 7. TODO(HARNESS)
- (매핑 없음, 사람 판단 필요 항목)
````

끝나면 CLAUDE.md 의 "변환 보고" 형식으로만 답한다.
