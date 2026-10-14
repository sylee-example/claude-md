---
description: iBatis 쿼리 1건 → MyBatis (통합 DB 매핑 자동 주입)
argument-hint: <AS-IS sqlMap.xml> <statementId> <TO-BE mapper.xml>
allowed-tools: Bash(python3 docs/harness/scripts/brief.py *)
disable-model-invocation: true
---
!`python3 docs/harness/scripts/brief.py query $0 $1`

---

# 지시

위 작업지시서의 "1. 변환 대상" statement 1건만 MyBatis 로 변환해서 `$2` 에 넣는다.

1. `$2` 가 없으면 `<mapper>` 골격(DOCTYPE 포함)으로 새로 만든다. 있으면 같은 id 의 statement 만 교체하거나 맨 끝에 추가한다. 다른 statement 는 건드리지 않는다.
2. namespace, resultType, parameterType 은 "4. 표준 예시" 규칙을 따른다. 모르면 `TODO(HARNESS)`.
3. 테이블·컬럼은 "2. 매핑" 표에 있는 이름만 쓴다. `MERGED` 는 통합 조건 추가, `DROPPED`·매핑 없음은 `TODO(HARNESS)`.
4. iBatis 문법은 "3. 변환 규칙" 표대로 바꾼다.
5. SQL 의미(조인, 조건, 정렬, 힌트)는 바꾸지 않는다.
6. 빌드·실행·테스트 하지 않는다.

끝나면 CLAUDE.md 의 "변환 보고" 형식으로만 답한다.
