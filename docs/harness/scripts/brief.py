#!/usr/bin/env python3
"""작업지시서 조립: 변환 대상 1건 + 관련 매핑 행 + 해당 변환 규칙 + 표준 예시만 출력.

저사양 모델에 파일 전체·매핑 전체를 주면 놓치고 지어낸다.
필요한 것만 스크립트가 골라서 준다 (모델이 찾게 하지 않는다).

사용:
  brief.py query  <AS-IS sqlMap.xml> <statementId> [첨부...]
  brief.py logic  <AS-IS .java>      <메서드명>     [첨부...]
  brief.py screen <AS-IS .jsp 또는 명세.md>         [첨부...]
첨부: 함께 볼 파일 (명세서, 화면 js 등). 내용을 그대로 붙인다.
"""
import re
import sys
from pathlib import Path

from check import camel, read, rows

HARNESS = Path(__file__).resolve().parent.parent
LANG = {'.xml': 'xml', '.java': 'java', '.jsp': 'jsp', '.js': 'javascript', '.ts': 'ts',
        '.tsx': 'tsx', '.md': 'markdown', '.sql': 'sql'}
BIG_UNIT_LINES = 300  # 이보다 크면 저사양 모델 품질 급락 → 더 잘게 나누라고 경고
NOT_TABLES = {'DUAL', 'SYSDATE', 'SYSTIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIMESTAMP'}


def stop(msg):
  # stdout 으로 내보내야 슬래시 명령 주입 시 모델이 그대로 받는다
  print(f'# 작업지시서 생성 실패\n\n{msg}\n\n작업하지 말고 이 메시지를 사용자에게 그대로 보고하고 멈출 것.')
  sys.exit(0)


def fence(content, lang=''):
  ticks = '`' * max(3, max((len(m) for m in re.findall(r'`+', content)), default=0) + 1)
  return f'{ticks}{lang}\n{content.rstrip()}\n{ticks}'


def extract_statement(xml, sid):
  sid = sid.split('.')[-1]
  m = re.search(rf'<(select|insert|update|delete|statement|procedure|sql)\b[^>]*\bid\s*=\s*"{re.escape(sid)}".*?</\1>',
                xml, re.S)
  if not m:
    stop(f'statement id 를 찾지 못함: {sid}')
  unit = m.group(0)
  # 참조하는 <sql> 조각, <resultMap> 도 같이 준다
  for ref in dict.fromkeys(re.findall(r'<include\s+refid\s*=\s*"([^"]+)"', unit)):
    frag = re.search(rf'<sql\b[^>]*\bid\s*=\s*"{re.escape(ref.split(".")[-1])}".*?</sql>', xml, re.S)
    if frag:
      unit += '\n\n<!-- include 조각 -->\n' + frag.group(0)
  for ref in dict.fromkeys(re.findall(r'\bresultMap\s*=\s*"([^"]+)"', unit)):
    rmap = re.search(rf'<resultMap\b[^>]*\bid\s*=\s*"{re.escape(ref.split(".")[-1])}".*?</resultMap>', xml, re.S)
    if rmap:
      unit += '\n\n<!-- resultMap -->\n' + rmap.group(0)
  return unit


def extract_method(src, name):
  decl = re.compile(rf'^[ \t]*(?:(?:public|protected|private|static|final|synchronized|abstract)\s+)*'
                    rf'[\w<>\[\],.? ]+\s+{re.escape(name)}\s*\([^)]*\)[^{{;]*\{{', re.M)
  m = decl.search(src)
  if not m:
    stop(f'메서드 선언을 찾지 못함: {name}')
  # ponytail: 문자열/주석 속 중괄호는 무시 못 함. 어긋나면 파일 끝까지 잘림 → 사람이 확인
  depth = 0
  for j in range(m.end() - 1, len(src)):
    if src[j] == '{':
      depth += 1
    elif src[j] == '}':
      depth -= 1
      if depth == 0:
        return src[m.start():j + 1]
  return src[m.start():]


def sql_tables(sql):
  """FROM/JOIN/INTO/UPDATE/USING 뒤 테이블명 (콤마 조인 포함)."""
  ctes = {n.upper() for n in re.findall(r'(?:\bWITH|,)\s*([A-Za-z_]\w*)\s+AS\s*\(', sql, re.I)}
  names = set()
  for m in re.finditer(r'\b(?:FROM|JOIN|INTO|UPDATE|USING)\s+([A-Za-z_][\w$#.]*(?:\s+[A-Za-z_]\w*)?'
                       r'(?:\s*,\s*[A-Za-z_][\w$#.]*(?:\s+[A-Za-z_]\w*)?)*)', sql, re.I):
    for part in m.group(1).split(','):
      names.add(part.split()[0].split('.')[-1].upper())
  return names - ctes - NOT_TABLES


def table(headers, data):
  if not data:
    return '(해당 없음)'
  lines = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
  lines += ['| ' + ' | '.join(str(c).replace('|', '\\|') for c in row) + ' |' for row in data]
  return '\n'.join(lines)


def mapping_section(text, kind):
  tokens = set(re.findall(r'[A-Za-z_]\w*', text))
  upper = {t.upper() for t in tokens}
  tables = [r for r in rows('tables.csv') if r['asis_table'].upper() in upper]
  cols = [r for r in rows('columns.csv')
          if (r['asis_column'].upper() in upper or camel(r['asis_column']) in tokens)
          and (kind != 'query' or r['asis_table'].upper() in upper)]
  saps = [r for r in rows('sap.csv') if r['rfc_function'] and r['rfc_function'] in tokens]

  out = ['## 2. 매핑 (이 대상에 나온 것만. 여기 없는 이름은 만들지 말 것)', '### 테이블']
  out.append(table(['AS-IS', 'TO-BE', '상태', '통합 조건', '비고'],
                   [[r['asis_table'], r['tobe_table'], r['status'], r['merge_cond'], r['note']] for r in tables]))
  out.append('### 컬럼')
  out.append(table(['AS-IS 테이블', 'AS-IS 컬럼', 'TO-BE 테이블', 'TO-BE 컬럼', 'TO-BE 필드(camel)', '변환 규칙'],
                   [[r['asis_table'], r['asis_column'], r['tobe_table'], r['tobe_column'],
                     camel(r['tobe_column']), r['rule']] for r in cols]))
  out.append('### SAP RFC → RAP')
  out.append(table(['RFC 함수', 'RFC 파라미터', 'RAP 경로', 'RAP 필드', 'HTTP', '비고'],
                   [[r['rfc_function'], r['rfc_param'], r['rap_path'], r['rap_field'], r['method'], r['note']]
                    for r in saps]))
  if kind == 'query':
    unmapped = sql_tables(text) - {r['asis_table'].upper() for r in rows('tables.csv')}
    if unmapped:
      out.append(f'### ⚠ 매핑 없는 테이블: {", ".join(sorted(unmapped))}')
      out.append('해당 부분은 변환하지 말고 `TODO(HARNESS): 매핑 없음 <테이블>` 주석을 남길 것.')
  return '\n\n'.join(out)


def pattern_section(kind):
  path = HARNESS / 'mapping' / 'patterns.md'
  if not path.exists():
    return ''
  sections = re.split(r'(?m)^(?=## )', read(path))
  return '\n\n'.join(s.strip() for s in sections if s.startswith('## ') and f'[{kind}]' in s.splitlines()[0])


def example_section(kind):
  d = HARNESS / 'examples' / kind
  files = sorted(p for p in d.rglob('*') if p.is_file() and not p.name.startswith('.')) if d.exists() else []
  if not files:
    return f'(표준 예시 없음 — docs/harness/examples/{kind}/ 를 채우면 품질이 크게 오른다)'
  return '\n\n'.join(f'### {p.relative_to(d)}\n' + fence(read(p), LANG.get(p.suffix, '')) for p in files)


def main():
  if len(sys.argv) < 3 or sys.argv[1] not in ('query', 'logic', 'screen'):
    stop('사용법: brief.py <query|logic|screen> <AS-IS 파일> [대상 id/메서드] [첨부...]')
  kind, src = sys.argv[1], sys.argv[2]
  if not Path(src).is_file():
    stop(f'파일 없음: {src}')
  text = read(src)

  if kind == 'query':
    if len(sys.argv) < 4:
      stop('query 는 statementId 가 필요함')
    target, attachments = sys.argv[3], sys.argv[4:]
    unit = extract_statement(text, target)
  elif kind == 'logic':
    if len(sys.argv) < 4:
      stop('logic 은 메서드명이 필요함')
    target, attachments = sys.argv[3], sys.argv[4:]
    unit = extract_method(text, target)
  else:
    target, attachments = '(파일 전체)', sys.argv[3:]
    unit = text

  out = ['# 작업지시서 (brief.py 자동 생성)']
  n = unit.count('\n') + 1
  if n > BIG_UNIT_LINES:
    out.append(f'> ⚠ 대상이 {n}줄로 큼. 결과가 나쁘면 더 작은 단위로 나눠서 다시 실행할 것.')
  out.append(f'## 1. 변환 대상: `{src}` / `{target}`\n\n' + fence(unit, LANG.get(Path(src).suffix, '')))
  out.append(mapping_section(unit, kind))
  out.append('## 3. 변환 규칙\n\n' + (pattern_section(kind) or '(patterns.md 없음)'))
  out.append('## 4. 표준 예시 (이 형태를 그대로 따를 것)\n\n' + example_section(kind))
  for a in attachments:
    if Path(a).is_file():
      out.append(f'## 첨부: `{a}`\n\n' + fence(read(a), LANG.get(Path(a).suffix, '')))
    else:
      out.append(f'## 첨부 없음: `{a}` (경로 확인)')
  print('\n\n'.join(out))


if __name__ == '__main__':
  main()
