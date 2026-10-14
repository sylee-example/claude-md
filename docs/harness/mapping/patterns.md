# 코드 변환 규칙

> brief.py 가 `## [query]`, `## [logic]`, `## [screen]` 태그가 붙은 섹션만 골라 작업지시서에 넣는다.
> 섹션을 추가할 때는 제목에 태그를 붙일 것. 모델 컨텍스트에 그대로 들어가므로 표 위주로 짧게 쓴다.

## [query] iBatis 2 → MyBatis 3 (Oracle)

| iBatis (AS-IS) | MyBatis (TO-BE) |
|---|---|
| `<sqlMap namespace="Cust">` | `<mapper namespace="Mapper 인터페이스 FQCN">` + `<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "https://mybatis.org/dtd/mybatis-3-mapper.dtd">` |
| `parameterClass` / `resultClass` | `parameterType` / `resultType` |
| `<resultMap class="..">` | `<resultMap type="..">` |
| `#param#` | `#{param}` |
| `#param:VARCHAR#` | `#{param,jdbcType=VARCHAR}` (Oracle 에서 null 들어올 수 있는 값은 jdbcType 유지) |
| `$param$` | `${param}` — 정렬 컬럼 등 화이트리스트 값만. 사용자 입력이면 `TODO(HARNESS): SQL injection` |
| `<dynamic prepend="WHERE">` | `<where>` (안쪽 첫 AND/OR 는 자동 제거) |
| `<isNotEmpty property="a" prepend="AND">` | `<if test="a != null and a != ''">AND ...</if>` |
| `<isEmpty property="a">` | `<if test="a == null or a == ''">` |
| `<isNotNull property="a">` / `<isNull>` | `<if test="a != null">` / `<if test="a == null">` |
| `<isEqual property="a" compareValue="Y">` | `<if test='a == "Y"'>` — `'Y'` 한 글자 작은따옴표는 char 로 비교돼서 항상 false. 큰따옴표로 감쌀 것 |
| `<isNotEqual ...>` | `<if test='a != "Y"'>` |
| `<isGreaterThan property="a" compareValue="0">` | `<if test="a gt 0">` (`gt` `gte` `lt` `lte` 사용, `<` 직접 쓰지 말 것) |
| `<isNotEmpty property="list">` (컬렉션) | `<if test="list != null and !list.isEmpty()">` |
| `<iterate property="ids" open="(" close=")" conjunction=",">#ids[]#</iterate>` | `<foreach collection="ids" item="id" open="(" separator="," close=")">#{id}</foreach>` (파라미터 자체가 List 면 `collection="list"`) |
| `<selectKey resultClass="long" keyProperty="id">SELECT SEQ.NEXTVAL FROM DUAL</selectKey>` | `<selectKey keyProperty="id" resultType="long" order="BEFORE">...</selectKey>` |
| `<procedure id="x">{call PKG.P(#a#)}</procedure>` | `<select id="x" statementType="CALLABLE">{call PKG.P(#{a})}</select>` |
| `<statement>` | 실제 동작에 맞게 `<select>`/`<update>` |
| `<![CDATA[ ... ]]>`, 힌트 `/*+ ... */` | 그대로 유지 |

- statement id 는 AS-IS 그대로 유지 (Mapper 메서드명과 같아야 함).
- `resultType` 은 DTO. 사내 MyBatis 설정 `mapUnderscoreToCamelCase=true` 가정 → SELECT 별칭은 TO-BE 컬럼명 그대로. (설정이 다르면 이 줄 수정)

## [query] 통합 DB 반영

- 테이블·컬럼 이름은 작업지시서 "매핑" 표에 있는 것만 사용. 없으면 `TODO(HARNESS): 매핑 없음 <이름>`.
- 상태 `MERGED`: SELECT/UPDATE/DELETE 는 WHERE 에 `통합 조건` 추가 (별칭 붙여서). INSERT 는 통합 조건의 컬럼에 그 값을 넣는다.
- 상태 `DROPPED`: 변환하지 말고 `TODO(HARNESS): 폐기 테이블 <이름>`.
- 컬럼 `변환 규칙` 이 있으면 반드시 적용 (예: 문자 날짜 → DATE).
- 바인드 변수명도 TO-BE 필드명(camel)으로: `#custNo#` → `#{customerId}`.
- 조인 조건, WHERE 의미, ORDER BY, 힌트는 바꾸지 않는다. "개선" 금지.

## [logic] Java 1.6 → Java 21 / Spring Boot 3.2

| AS-IS | TO-BE |
|---|---|
| `javax.servlet.*`, `javax.annotation.*`, `javax.validation.*` | `jakarta.*` |
| `HashMap` / 데이터셋으로 값 전달 | 요청·응답 DTO (Lombok, 형태는 examples/logic 따름) |
| raw `List`, `Map` | 제네릭 `List<CustomerDto>` |
| `@Autowired` 필드 주입 | `@RequiredArgsConstructor` + `private final` |
| `System.out`, commons-logging | `@Slf4j` + `log.info/debug` |
| `Date`, `Calendar`, `SimpleDateFormat` | `LocalDate`, `LocalDateTime`, `DateTimeFormatter` |
| `try { } finally { close() }` | try-with-resources |
| `new Integer(x)` | `Integer.valueOf(x)` |
| `StringBuffer` | `StringBuilder` |
| `e.printStackTrace()`, 에러코드 리턴 | 사내 공통 예외 throw (examples/logic) |

- 레이어: Controller(`@RestController`, `@Valid`) → Service(`@Service`) → Mapper(`@Mapper` 인터페이스).
- 트랜잭션: 조회 서비스 `@Transactional(readOnly = true)`, 저장/수정/삭제 `@Transactional`.
- API 응답은 사내 공통 응답 래퍼만 사용 (examples/logic).

## [logic] iBatis 호출 → MyBatis Mapper

| AS-IS | TO-BE |
|---|---|
| `sqlMapClient.queryForList("Cust.selectCustList", p)` | `customerMapper.selectCustList(p)` → `List<Dto>` |
| `queryForObject(...)` | 단건 `Dto` 반환 (없음 처리는 서비스에서) |
| `insert` / `update` / `delete` | `int` 반환 |
| `startTransaction` / `commitTransaction` / `endTransaction` | 서비스 메서드 `@Transactional` 로 대체 (수동 커밋 코드 삭제) |
| `startBatch` / `executeBatch` | `TODO(HARNESS): 배치 처리 방식 결정 필요` |

- Mapper 메서드명 = statement id. Mapper XML 은 `/convert-query` 로 따로 변환.

## [logic] nexcore → Spring

> ⚠ 아래 왼쪽 열은 틀이다. 실제 nexcore 클래스·메서드명은 사내 AS-IS 코드 보고 채울 것.

| nexcore (AS-IS, 예) | TO-BE |
|---|---|
| 입력 데이터셋에서 필드 읽기 (예: `getField("CUST_NO")`) | 요청 DTO getter (TO-BE 이름: `getCustomerId()`) |
| 출력 데이터셋 / 레코드셋 | 응답 DTO / `List<응답 DTO>` |
| 업무 컴포넌트 메서드 | `@Service` 메서드 |
| 화면이 거래(서비스) ID 로 호출 | REST 엔드포인트 (조회 `@GetMapping`, 저장 `@PostMapping`) |
| 프레임워크 공통 예외·메시지 | 사내 공통 예외 (examples/logic) |
| 온라인 컨텍스트 (사용자·세션 정보) | 사내 인증 컨텍스트 (examples/logic) |

## [logic] SAP RFC (JCo) → RAP

| JCo (AS-IS) | RAP (TO-BE) |
|---|---|
| `JCoDestinationManager.getDestination(..)` | 사내 공통 SAP 클라이언트 주입 (examples/logic). HTTP 클라이언트 직접 생성 금지 |
| `getFunction("Z_..")` | 매핑 표의 `RAP 경로` |
| `getImportParameterList().setValue("I_X", v)` | 매핑 표의 `RAP 필드` 로 `$filter` 또는 키 |
| `function.execute(dest)` | 매핑 표의 `HTTP` (조회 GET, 생성·수정 POST/PATCH) |
| `getExportParameterList().getString("E_X")` | 응답 JSON 필드 → DTO |
| `getTableParameterList().getTable("ET_X")` 루프 | 응답 `value` 배열 / `$expand` 하위 엔티티 → `List<Dto>` |
| `JCoException` 처리 | 사내 공통 예외로 변환 |

- 매핑 표에 없는 RFC 는 `TODO(HARNESS): RAP 매핑 없음 <함수명>`. 경로·필드 지어내기 금지.
- 인증, CSRF 토큰, 재시도는 공통 SAP 클라이언트 책임. 서비스 코드에서 다루지 않는다.

## [screen] JSP → React 18 + FSD

레이어 (위 → 아래): `app` → `pages` → `widgets` → `features` → `entities` → `shared`.
위는 아래만 import. 같은 레이어의 다른 슬라이스 import 금지 (check.py 가 검사).

| JSP 요소 | TO-BE 위치 |
|---|---|
| 화면 1개 (jsp) | `pages/<screen>/ui/<Screen>Page.tsx` + 라우트 파일 (tanstack router, 위치는 examples 따름) |
| 조회조건 영역 | `features/<screen>-search/ui/<Screen>SearchForm.tsx` (antd `Form`) |
| 그리드 | `widgets/<screen>-grid/ui/<Screen>Grid.tsx` (ag-grid) |
| `$.ajax`, form submit, 프레임워크 호출 | `entities/<entity>/api/` 의 tanstack query 훅 (`use<Xxx>Query`, `use<Xxx>Mutation`) |
| 요청·응답 필드 | `entities/<entity>/model/types.ts` (TO-BE camel 필드명) |
| 화면 간 공유 상태 | zustand store (`model/store.ts`). 화면 안에서만 쓰는 상태는 `useState` |
| 서버 렌더링 값 (`${..}`, `<%= %>`, JSTL) | API 응답 또는 라우트 search params |
| `alert` / `confirm` | antd `App.useApp()` 의 `message` / `modal.confirm` |
| `window.open` 팝업 | antd `Modal` 컴포넌트 |
| 공통코드 콤보 | 사내 공통 훅·컴포넌트 (examples/screen) |
| JSP include 헤더·메뉴 | 변환 안 함 (app 레이아웃 담당) |

- `any` 금지. 모르는 타입은 `unknown` + 타입 가드, 또는 `TODO(HARNESS)`.
- 서버 호출은 query 훅으로만. 컴포넌트에서 fetch/axios 직접 호출 금지.
- queryKey: `['<entity>', 조건객체]`.

## [screen] AS-IS 그리드 → ag-grid enterprise

| AS-IS 그리드 속성 | ag-grid |
|---|---|
| 컬럼 정의 | `const columnDefs: ColDef<RowType>[]` — `field` 는 TO-BE camel 필드명 |
| 헤더 텍스트 | `headerName` |
| 폭·정렬 | `width`, `cellClass`, 숫자는 `type: 'numericColumn'` |
| 숫자·날짜 포맷 | `valueFormatter` |
| 편집 | `editable: true` + `cellEditor` (`agTextCellEditor`, `agSelectCellEditor`) |
| 엑셀 다운로드 | `gridApi.exportDataAsExcel()` |

- 행 선택, 합계행 등은 ag-grid 버전마다 API 가 다르다 → examples/screen 의 사용법을 그대로 따른다.
- 라이선스 키는 앱 진입점에서 한 번만 설정. 화면 코드에서 설정 금지.
