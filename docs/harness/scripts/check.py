#!/usr/bin/env python3
"""변환 결과 정적 검증 (빌드/컴파일 없음, 표준 라이브러리만 사용).

사용:
  python3 check.py <파일...>     사람이 직접 실행. 위반 있으면 exit 1
  (PostToolUse 훅)               stdin JSON 의 tool_input.file_path 검사. 위반 있으면 exit 2
                                 → stderr 가 모델에게 전달되어 그 항목만 고치게 함

원칙: 오탐 없는 규칙만 둔다. 오탐은 저사양 모델을 헛돌게 만들어 토큰만 쓴다.
'TODO(HARNESS)' 또는 'AS-IS' 가 들어간 줄은 검사하지 않는다 (사람 확인용 표식).
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

MAPPING = Path(__file__).resolve().parent.parent / 'mapping'
TARGET_EXTS = {'.xml', '.sql', '.java', '.ts', '.tsx'}
SKIP_LINE = re.compile(r'TODO\(HARNESS\)|AS-IS')

# FSD 레이어: 아래 → 위. 위 레이어는 아래 레이어만 import 가능
FSD_LAYERS = ['shared', 'entities', 'features', 'widgets', 'pages', 'app']
FSD_ALIAS = '@/'  # tsconfig paths 의 src 별칭. 다르면 수정

RULES = {
  'mapper': [
    (r'<sqlMap\b', 'iBatis <sqlMap> → <mapper namespace="Mapper 인터페이스 FQCN">'),
    (r'\bparameterClass=', 'parameterClass → parameterType'),
    (r'\bresultClass=', 'resultClass → resultType'),
    (r'<(isNotEmpty|isEmpty|isNotNull|isNull|isEqual|isNotEqual|isGreaterThan|isGreaterEqual|'
     r'isLessThan|isLessEqual|isPropertyAvailable|isNotPropertyAvailable|isParameterPresent|'
     r'isNotParameterPresent)\b', 'iBatis 동적 태그 → <if test="...">'),
    (r'<dynamic\b', '<dynamic> → <where> 또는 <trim>'),
    (r'<iterate\b', '<iterate> → <foreach>'),
    (r'#[A-Za-z_][\w.\[\]]*(:\w+)?#', '#param# → #{param}'),
    (r'\$[A-Za-z_][\w.]*\$', '$param$ → ${param} (정렬 컬럼 등 화이트리스트 값만)'),
  ],
  'java': [
    (r'\bjavax\.(servlet|annotation|validation|persistence)\b', 'javax.* → jakarta.* (Spring Boot 3)'),
    (r'\bcom\.ibatis\b|\bSqlMapClient', 'iBatis API → @Mapper 인터페이스'),
    (r'(?i)\bnexcore\b', 'nexcore 의존 제거 → Spring 표준 (patterns.md)'),
    (r'\bcom\.sap\.conn\.jco\b|\bJCo[A-Z]\w*', 'SAP JCo(RFC) → RAP 호출 (patterns.md)'),
    (r'@Autowired', '필드 주입 → 생성자 주입 (@RequiredArgsConstructor + private final)'),
    (r'System\.(out|err)\.print', 'System.out → @Slf4j log'),
  ],
  'ts': [
    (r':\s*any\b|\bas\s+any\b|<any\b|,\s*any\s*>|\bany\[\]', 'any 금지 → 구체 타입 또는 unknown'),
    (r'''from\s+['"]react-router(-dom)?['"]''', 'react-router → @tanstack/react-router'),
    (r'''from\s+['"](redux|@reduxjs/toolkit|react-redux|recoil|jotai)['"]''', '상태관리 → zustand'),
    (r'''from\s+['"]jquery['"]|\$\.ajax''', 'jQuery/ajax → tanstack query 훅'),
    (r'(?<![\w.])(alert|confirm)\(|window\.(alert|confirm)\(', 'alert/confirm → antd message / Modal.confirm'),
  ],
}
KIND = {'.xml': 'mapper', '.sql': 'mapper', '.java': 'java', '.ts': 'ts', '.tsx': 'ts'}


def read(path):
  raw = Path(path).read_bytes()
  for enc in ('utf-8', 'cp949'):
    try:
      return raw.decode(enc)
    except UnicodeDecodeError:
      pass
  return raw.decode('utf-8', errors='replace')


def rows(name):
  path = MAPPING / name
  if not path.exists():
    return []
  with open(path, encoding='utf-8-sig') as f:
    return [r for r in csv.DictReader(f)]


def camel(name):
  head, *rest = name.lower().split('_')
  return head + ''.join(w.capitalize() for w in rest)


def old_name_patterns():
  """AS-IS 테이블/컬럼명 잔존 검사용 정규식 2개 (대문자 스네이크, camelCase)."""
  tables, cols = rows('tables.csv'), rows('columns.csv')
  new = {r['tobe_table'].upper() for r in tables + cols} | {r['tobe_column'].upper() for r in cols}
  old = {r['asis_table'].upper() for r in tables} | {r['asis_column'].upper() for r in cols}
  # ponytail: '_' 없는 단어(NAME, TYPE 등)는 일반 단어와 겹쳐 오탐 → 제외. 잡고 싶으면 SQL 파서 도입
  old = {n for n in old - new if n and '_' in n}
  if not old:
    return None, None
  new_camel = {camel(n) for n in new}
  old_camel = {camel(n) for n in old} - new_camel
  snake = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, old), key=len, reverse=True)) + r')\b', re.I)
  cam = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, old_camel), key=len, reverse=True)) + r')\b') if old_camel else None
  return snake, cam


def fsd_errors(path, text):
  abs_path = Path(path).resolve()
  parts = abs_path.parts
  if 'src' not in parts:
    return []
  i = len(parts) - 1 - parts[::-1].index('src')
  rel = parts[i + 1:]
  if len(rel) < 2 or rel[0] not in FSD_LAYERS:
    return []
  layer = rel[0]
  slice_ = rel[1] if len(rel) > 2 else None
  src_root = Path(*parts[:i + 1])
  errors = []
  for no, line in enumerate(text.splitlines(), 1):
    for m in re.finditer(r'''(?:from|import)\s*\(?\s*['"]([^'"]+)['"]''', line):
      spec = m.group(1)
      if spec.startswith(FSD_ALIAS):
        target = spec[len(FSD_ALIAS):].split('/')
      elif spec.startswith('.'):
        resolved = Path(os.path.normpath(abs_path.parent / spec))
        try:
          target = list(resolved.relative_to(src_root).parts)
        except ValueError:
          continue
      else:
        continue
      if not target or target[0] not in FSD_LAYERS or '@x' in target:
        continue
      t_layer = target[0]
      t_slice = target[1] if len(target) > 1 else None
      if FSD_LAYERS.index(t_layer) > FSD_LAYERS.index(layer):
        errors.append(f'{no}행: FSD 위반 - {layer} 가 상위 레이어 {t_layer} 를 import ({spec})')
      elif t_layer == layer and layer not in ('shared', 'app') and t_slice != slice_:
        errors.append(f'{no}행: FSD 위반 - 같은 레이어의 다른 슬라이스 import ({spec}). 하위 레이어로 내리거나 상위에서 조합')
  return errors


def check_file(path):
  ext = Path(path).suffix.lower()
  if ext not in TARGET_EXTS or not Path(path).is_file():
    return []
  text = read(path)
  lines = text.splitlines()
  errors = []

  for pattern, msg in RULES[KIND[ext]]:
    rx = re.compile(pattern)
    for no, line in enumerate(lines, 1):
      if not SKIP_LINE.search(line) and rx.search(line):
        errors.append(f'{no}행: {msg}')

  snake, cam = old_name_patterns()
  for no, line in enumerate(lines, 1):
    if SKIP_LINE.search(line):
      continue
    found = set()
    if snake:
      found |= {m.group(1) for m in snake.finditer(line)}
    if cam:
      found |= {m.group(1) for m in cam.finditer(line)}
    if found:
      errors.append(f'{no}행: AS-IS 이름 잔존 {sorted(found)} → mapping/columns.csv·tables.csv 의 TO-BE 이름으로')

  if KIND[ext] == 'ts':
    errors += fsd_errors(path, text)
  return errors


def main():
  if len(sys.argv) > 1:
    failed = False
    for path in sys.argv[1:]:
      errors = check_file(path)
      if errors:
        failed = True
        print(f'[검증 실패] {path}')
        print('\n'.join(f'  - {e}' for e in errors))
    sys.exit(1 if failed else 0)

  # 훅 모드
  data = json.load(sys.stdin)
  path = data.get('tool_input', {}).get('file_path', '')
  errors = check_file(path) if path else []
  if errors:
    print(f'[검증 실패] {path}\n' + '\n'.join(f'- {e}' for e in errors), file=sys.stderr)
    print('위 항목만 고칠 것. 같은 오류가 2번 반복되면 해당 줄에 TODO(HARNESS) 사유를 남기고 멈출 것.', file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
  main()
