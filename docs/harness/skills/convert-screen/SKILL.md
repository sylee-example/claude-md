---
description: 검토 끝난 화면 명세 → React 코드 생성 (한 번에 한 파트 api|grid|page)
argument-hint: <AS-IS .jsp> <api|grid|page>
allowed-tools: Bash(python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" *)
disable-model-invocation: true
---
!`python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" convert-screen $ARGUMENTS`

---

# 지시

작업지시서가 "# 작업지시서 생성 실패" 로 시작하면 아래는 무시하고, 그 메시지만 사용자에게 보고하고 끝낸다.

"1. 변환 대상" 의 화면 명세(사람이 검토 완료)가 기준이다. 이번 호출에서는 작업지시서 끝의 **"이번에 만들 파트" 만** 만든다.

| 파트 | 만들 파일 (경로는 표준 예시 규칙이 우선) | 내용 |
|---|---|---|
| api | `entities/<엔티티>/model/types.ts`, `entities/<엔티티>/api/<엔티티>Api.ts` | 명세 "4. API" → 요청/응답 타입 + tanstack query 훅 |
| grid | `widgets/<화면 슬러그>-grid/ui/<Screen>Grid.tsx` | 명세 "2. 그리드" → `ColDef<응답 타입>[]` + AgGridReact |
| page | `features/<화면 슬러그>-search/ui/<Screen>SearchForm.tsx`, `pages/<화면 슬러그>/ui/<Screen>Page.tsx`, 라우트 파일 | 명세 "1. 조회 조건" 폼 + 화면 조립 (api·grid 는 import 만) |

1. 순서는 api → grid → page. 앞 파트 파일이 없으면 만들지 말고 "앞 파트 필요" 라고 답하고 멈춘다.
2. 형태는 "4. 표준 예시" 를 그대로 따른다.
3. 명세에 없는 필드·버튼·API 를 추가하지 않는다.
4. `any` 금지. FSD 규칙: 위 레이어는 아래 레이어만 import.
5. 빌드·실행·테스트 하지 않는다 (npm, npx, tsc, vite 모두 금지).

끝나면 CLAUDE.md 의 "변환 보고" 형식으로만 답한다.
