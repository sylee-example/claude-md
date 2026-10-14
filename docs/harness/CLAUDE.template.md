# 레거시 → TO-BE 전환 규칙

> 저사양 LLM 용. 짧게 유지할 것. 세부 변환 규칙은 docs/harness/mapping/patterns.md.

## 절대 금지
1. 빌드·컴파일·테스트·실행 금지: gradle, gradlew, mvn, javac, java, npm, npx, yarn, pnpm, node, tsc, vite.
   빌드 확인은 사용자가 직접 한다. 명령이 거부되면 다른 방법으로 우회하지 말고 다음 단계로 간다.
2. 의존성 추가·설치 금지 (build.gradle, package.json 수정 포함).
3. 매핑 표에 없는 테이블·컬럼·RAP 경로를 지어내지 않는다 → `TODO(HARNESS): 사유` 주석을 남긴다.
4. 요청받은 파일 외 수정 금지. 리팩터링·"개선" 금지.
5. 작업지시서에 없는 파일을 찾아 돌아다니지 않는다.

## 작업 방식
- 변환은 스킬로만 (사용자가 실행): /convert-query, /spec-logic, /convert-logic, /spec-screen, /convert-screen
- 한 번에 한 단위만. 단위가 끝나면 사용자가 /clear 한다.
- 파일 저장 후 `[검증 실패]` 메시지가 오면 그 항목만 고친다.
  같은 오류가 2번 반복되면 그 줄에 `TODO(HARNESS): 사유` 를 남기고 멈춘다.
- TODO 주석 형식: Java/TS `// TODO(HARNESS): 사유`, SQL `/* TODO(HARNESS): 사유 */`, XML `<!-- TODO(HARNESS): 사유 -->`

## 끝나면 이 형식으로만 보고
```
### 변환 보고
- 생성/수정 파일: (경로 목록)
- TODO(HARNESS): (개수 / 위치 / 사유)
- 사용자 확인 필요: (빌드·동작 확인할 것)
```
