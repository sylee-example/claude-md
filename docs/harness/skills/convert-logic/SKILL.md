---
description: 검토 끝난 로직 명세 → Controller/Service/DTO/Mapper 인터페이스 생성
argument-hint: <AS-IS .java> <메서드명>
allowed-tools: Bash(python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" *)
disable-model-invocation: true
---
!`python3 "${CLAUDE_PROJECT_DIR}/docs/harness/scripts/brief.py" convert-logic $ARGUMENTS`

---

# 지시

작업지시서가 "# 작업지시서 생성 실패" 로 시작하면 아래는 무시하고, 그 메시지만 사용자에게 보고하고 끝낸다.

작업지시서 끝의 "명세서" 가 기준이다 (사람이 검토 완료). 명세서와 AS-IS 코드가 다르면 명세서를 따른다.

1. 명세 "0. 생성 파일" 의 파일만 만든다. 이미 있는 파일이면 해당 메서드만 추가한다.
2. 형태(어노테이션, 응답 래퍼, 예외, DTO 모양)는 "4. 표준 예시" 를 그대로 따른다.
3. Mapper 인터페이스 메서드명 = statement id. Mapper XML 은 만들지 않는다 (/convert-query 담당).
4. 명세 "3. 처리 순서" 를 순서대로 코드로 옮긴다. 빠뜨리거나 덧붙이지 않는다.
5. SAP 호출은 "3. 변환 규칙" 의 RAP 표대로, 공통 SAP 클라이언트로만 한다.
6. 빌드·컴파일·테스트 하지 않는다.

끝나면 CLAUDE.md 의 "변환 보고" 형식으로만 답한다.
