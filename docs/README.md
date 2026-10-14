# 레거시 → TO-BE 전환 하네스

사내 저사양 LLM 을 Claude Code(claude CLI)로 쓸 때 쿼리·로직·화면 변환 품질을 끌어올리기 위한 작업 틀.

- AS-IS: Java 1.6, JSP/Servlet, iBatis + Oracle, nexcore, SAP RFC
- TO-BE: Java 21, Spring Boot 3.2, MyBatis + Oracle, Gradle, Lombok / React 18 + TypeScript, FSD, TanStack Router·Query, Zustand, ag-grid enterprise, antd / SAP RAP
- 통합 DB: 테이블·컬럼명 전면 변경, 데이터 없던 테이블은 통합

## 1. 핵심 원칙

모델을 똑똑하게 만들 수는 없다. **모델이 할 일을 줄이고, 틀리면 스크립트가 잡는다.** 결과가 나쁘면 모델 탓이 아니라 하네스(매핑·규칙·예시·단위 크기)를 고친다.

| 저사양 모델 실패 | 원인 | 하네스 대응 |
|---|---|---|
| 테이블·컬럼명을 지어냄 | 매핑을 모름 | `brief.py` 가 대상에 나온 매핑 행만 주입, `check.py` 가 AS-IS 이름 잔존 검사 |
| 큰 파일에서 놓침 | 컨텍스트 한계 | statement 1개, 메서드 1개만 잘라서 줌 |
| 사내 표준과 다른 코드 | 표준을 모름 | 표준 예시(골든 코드)를 매번 주입 |
| 빌드 → 에러 → 수정 무한 반복 | 빌드 실행 | 빌드·테스트·설치 명령 차단. 빌드 확인은 사람이 직접 |
| 화면 전체를 한 번에 → 엉망 | 작업이 너무 큼 | 명세 → (사람 검토) → 파트별 생성, 2단계 |
| 같은 오류를 계속 고침 | 자기 교정 능력 부족 | 2회 반복 시 `TODO(HARNESS)` 남기고 정지 |
| 엉뚱한 파일 탐색 | 도구가 많음 | 도구를 Read/Edit/Write/Bash 로 제한 |

## 2. 구성

```
docs/
  README.md                     이 문서
  harness/
    CLAUDE.template.md          TO-BE 루트 CLAUDE.md 에 넣을 규칙 (빌드 금지 포함)
    settings.json               .claude/settings.json 용: 빌드 명령 deny + 저장 시 정적 검증 훅
    mapping/
      tables.csv                테이블 매핑 (RENAMED / MERGED / DROPPED)
      columns.csv               컬럼 매핑
      sap.csv                   SAP RFC → RAP 매핑
      patterns.md               코드 변환 규칙 ([query] [logic] [screen] 태그별)
    commands/                   .claude/commands/ 로 복사할 슬래시 명령
      convert-query.md          iBatis 쿼리 1건 → MyBatis
      spec-logic.md             AS-IS 메서드 → 로직 명세
      convert-logic.md          로직 명세 → Controller/Service/DTO/Mapper
      spec-screen.md            AS-IS JSP → 화면 명세
      convert-screen.md         화면 명세 → React (api | grid | page)
    scripts/
      brief.py                  작업지시서 조립 (대상 1건 + 관련 매핑 + 규칙 + 예시)
      check.py                  정적 검증 (빌드 아님, 표준 라이브러리만)
      test_harness.py           위 두 스크립트 자체 테스트
    examples/                   (직접 만들 것) 표준 예시 — 6장 참고
  specs/                        (작업하면서 생김) 로직·화면 명세서
```

## 3. 설치 (TO-BE 프로젝트에)

```bash
TOBE=<TO-BE 프로젝트 경로>
cp -r docs "$TOBE/"
mkdir -p "$TOBE/.claude/commands"
cp docs/harness/commands/*.md "$TOBE/.claude/commands/"
```

그다음 직접 병합 (덮어쓰기 주의):

1. `docs/harness/settings.json` → `$TOBE/.claude/settings.json`. 기존 파일이 있으면 `permissions.deny` 와 `hooks` 만 합친다.
2. `docs/harness/CLAUDE.template.md` 내용 → `$TOBE/CLAUDE.md` 맨 위에 붙인다.
3. `mapping/*.csv` 의 예시 행을 지우고 실제 매핑으로 채운다 (5장).
4. `examples/` 를 채운다 (6장).
5. 확인: `python3 docs/harness/scripts/test_harness.py` → `OK`

> Windows 라면 settings.json 과 commands/*.md 의 `python3` 를 `python` 으로 바꾼다. PowerShell 도구를 쓰면 deny 에 `PowerShell(gradle *)` 같은 규칙도 추가한다.

## 4. 실행과 작업 흐름

```bash
cd $TOBE
claude --tools "Read,Edit,Write,Bash" --disallowedTools "mcp__*" --add-dir <AS-IS 소스 경로>
```

- `--tools`: 도구 정의를 줄여 컨텍스트를 아끼고 엉뚱한 행동을 줄인다. **Bash 는 빼면 안 된다** — 슬래시 명령의 작업지시서 주입(`!` 실행)이 Bash 권한으로 돌기 때문에 빼면 거부된다.
- `--add-dir`: AS-IS 소스를 읽기 위해.
- **단위 하나 끝날 때마다 `/clear`.** 이전 작업이 컨텍스트에 남으면 저사양 모델은 섞어 버린다.

### 쿼리
```
/convert-query <AS-IS sqlMap.xml> <statementId> <TO-BE mapper.xml>
```

### 로직 (서비스 메서드 단위)
```
/spec-logic    <AS-IS .java> <메서드명> docs/specs/logic/<이름>.md
   → 사람이 명세 검토·수정 후 상태를 "검토 완료"로 변경
/convert-logic <AS-IS .java> <메서드명> docs/specs/logic/<이름>.md
   → 명세 "4. 호출하는 쿼리" 의 statement 마다 /convert-query
```

### 화면 (JSP 단위)
```
/spec-screen    <AS-IS .jsp> docs/specs/screen/<이름>.md [관련 js...]
   → 사람이 명세 검토·수정 후 "검토 완료"
/convert-screen docs/specs/screen/<이름>.md api
/convert-screen docs/specs/screen/<이름>.md grid
/convert-screen docs/specs/screen/<이름>.md page
```

명세 단계가 있는 이유: 명세(표)를 검토하는 것이 생성된 코드를 검토하는 것보다 훨씬 싸고, 저사양 모델도 "분석"과 "생성"을 나누면 각각은 해낸다.

### 각 명령 안에서 일어나는 일
1. `brief.py` 가 **결정적으로** 작업지시서를 만든다: 대상 1건 추출, 거기 나온 이름의 매핑 행만, 해당 태그의 변환 규칙, 표준 예시.
2. 모델은 지시서와 고정 양식만 보고 작업한다.
3. 파일을 저장할 때마다 `check.py` 훅이 돌고, 위반이 있으면 모델에게 돌려보낸다 (exit 2).
4. 모델은 고정 형식의 "변환 보고"(파일 목록 / TODO / 사용자 확인 필요)로 끝낸다.

## 5. 매핑 작성법 (하네스 품질 = 매핑 품질)

**tables.csv**

| 열 | 내용 |
|---|---|
| asis_table / tobe_table | 테이블명 |
| status | `RENAMED` 이름만 변경 / `MERGED` 다른 테이블로 통합 / `DROPPED` 폐기 |
| merge_cond | MERGED 일 때 TO-BE 에서 이 데이터를 구분하는 조건. 예: `CUST_TYPE_CD = 'CORP'` (SELECT 는 WHERE 에 추가, INSERT 는 값 세팅) |
| note | 사람·모델이 볼 메모 |

**columns.csv**: `asis_table, asis_column, tobe_table, tobe_column, rule`. `rule` 에 타입·값 변환을 적는다 (예: `VARCHAR2(8) yyyymmdd → DATE`). camelCase 필드명은 스크립트가 만든다.

**sap.csv**: RFC 함수 1개당 `rfc_param` 이 빈 행 1개(경로·HTTP 메서드) + 파라미터별 행.

**patterns.md**: 틀린 문법 변환을 발견하면 해당 태그 섹션의 표에 행을 추가한다. nexcore 섹션은 틀만 있으므로 사내 코드를 보고 채운다.

> 매핑은 DB 이관 정의서에서 뽑는다. 사람이 손으로 쓰지 말고 엑셀 → CSV 로 내보낸다 (UTF-8).

## 6. 표준 예시 채우기 (효과가 가장 큼)

첫 화면 하나는 **사람이 직접** 변환하고 그 결과를 예시로 넣는다. 저사양 모델은 규칙 설명보다 예시를 훨씬 잘 따라 한다.

```
docs/harness/examples/
  query/    Mapper XML 1개 (동적 조건, foreach, 통합 조건 포함)
  logic/    Controller, Service, 요청·응답 DTO, Mapper 인터페이스
            + 공통 응답 래퍼·공통 예외·공통 SAP 클라이언트 사용 예 1건씩
  screen/   types.ts, xxxApi.ts (query 훅), Grid.tsx, SearchForm.tsx, Page.tsx, 라우트 파일
```

- 매번 컨텍스트에 통째로 들어가므로 **유형별 300줄 이내**로 작게 유지한다.
- 경로·파일명 규칙은 예시가 기준이다 (명령 파일의 기본 경로보다 우선).

## 7. 빌드 금지 장치

- `settings.json` 의 `permissions.deny`: gradle/gradlew/mvn/javac/java/npm/npx/yarn/pnpm/node/tsc/vite.
  `cd backend && ./gradlew build` 같은 복합 명령도 차단된다 (서브 명령별 검사, 실제로 확인함).
  `sh -c '...'` 처럼 감싼 형태는 못 막는다 → CLAUDE.md 규칙으로 보완. 그래도 시도하면 PreToolUse 훅을 추가한다.
- 저장 시 도는 `check.py` 는 빌드가 아니다. 표준 라이브러리로 텍스트만 검사하고 파일당 1초도 안 걸린다.
- 빌드·동작 확인은 사람이 한다. 빌드 전에 아래부터 본다:

```bash
python3 docs/harness/scripts/check.py <파일...>     # 일괄 정적 검사
grep -rn "TODO(HARNESS)" src/                        # 모델이 판단을 넘긴 곳
```

## 8. 운영 루프 (결과가 나쁠 때 고칠 곳)

| 증상 | 고칠 곳 |
|---|---|
| 테이블·컬럼명이 틀림 | `columns.csv`, `tables.csv` |
| 문법 변환이 틀림 (같은 실수 반복) | `patterns.md` 표에 행 추가 |
| 구조·스타일이 표준과 다름 | `examples/` |
| 모델이 매번 놓치는 위반 | `check.py` 의 `RULES` 에 정규식 추가 (오탐 없는 것만) |
| 결과가 전반적으로 엉망 | 단위를 더 작게 (메서드 분리, 쿼리 1건씩) |

**효과 측정**: 사람이 이미 변환한 단위 10~20개를 평가셋으로 잡고, 하네스를 고칠 때마다 다시 돌려 `check.py` 통과율, TODO 수, 사람이 고친 줄 수를 비교한다. 측정 없이 고치면 감으로 고치는 것이다.

## 9. 한계

- `check.py` 는 오탐 없는 규칙만 둔다. 못 잡는 것: 매핑에 없는 TO-BE 이름을 지어낸 경우, 로직 의미 오류 → 명세 검토와 사람 빌드로 잡는다. 필요해지면 TO-BE 스키마(JSON) + SQL 파서(sqlglot) 검사를 추가한다.
- `_` 가 없는 AS-IS 컬럼명(NAME, TYPE 등)은 일반 단어와 겹쳐서 잔존 검사에서 뺐다.
- 메서드 추출은 문자열·주석 안의 중괄호에 약하다. 잘림이 보이면 메서드를 직접 붙여 넣는다.
- AS-IS 소스는 UTF-8 → CP949 순으로 읽는다. 다른 인코딩이면 `check.py` 의 `read()` 를 수정한다.
- 사내 LLM 접속 설정(`ANTHROPIC_BASE_URL` 등)은 이 문서 범위 밖이다.
