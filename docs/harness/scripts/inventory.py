#!/usr/bin/env python3
"""사전 점검: AS-IS 전체에서 변환 단위 목록과 매핑 누락을 뽑는다. 모델을 쓰지 않는다.

사용:
  python3 docs/harness/scripts/inventory.py --list backend.csv --list frontend.csv --asis-root <AS-IS 루트>
  python3 docs/harness/scripts/inventory.py --scan <AS-IS 루트>

  --list       경로 목록 파일 (CSV/TXT, 여러 개 가능). 형식 무관 — 각 칸에서 .xml/.java/.jsp 로 끝나는 값을 경로로 본다
  --asis-root  목록 안 상대경로의 기준 폴더 (기본: 현재 폴더)
  --scan       목록 대신 폴더를 직접 훑는다
  --tobe       'AS-IS: <키>' 추적 주석을 찾을 TO-BE 루트 (기본: 프로젝트 루트)
  --out        결과 폴더 (기본: docs/inventory)

결과 (실행마다 새로 씀 — 직접 고치지 말 것. Excel 에서 바로 열림):
  units.csv         변환 단위 + 명세/변환 상태 + 다음에 실행할 명령
  mapping-gaps.csv  매핑 누락 테이블·RFC, 폐기 테이블 사용처 (사용 횟수 많은 순)
"""
import argparse
import csv
import io
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from brief import PROJECT, SCREEN_PARTS, SPEC_DONE, extract_statement, spec_path, sql_tables, unit_key
from check import read, rows

UNIT_EXTS = ('.xml', '.java', '.jsp')
TOBE_EXTS = {'.xml', '.java', '.ts', '.tsx'}
SKIP_DIRS = {'node_modules', 'target', 'build', 'bin', 'classes', 'dist', 'docs'}
STATEMENT = re.compile(r'<(select|insert|update|delete|statement|procedure)\b[^>]*\bid\s*=\s*"([^"]+)"')
PUBLIC_METHOD = re.compile(r'^[ \t]*public\s+(?:(?:static|final|synchronized|abstract)\s+)*[\w<>\[\],.? ]+?\s+(\w+)\s*\(', re.M)
# ponytail: 변환 대상이 아닌 메서드를 이름으로만 거른다. 그래도 남는 잡음은 units.csv 에서 경로로 필터
SKIP_METHOD = re.compile(r'^((get|set|is)[A-Z]\w*|toString|equals|hashCode|main)$')
RFC_CALL = re.compile(r'getFunction\s*\(\s*"([^"]+)"')
TRACE = re.compile(r'AS-IS:\s*(\S+)')


def walk(root, exts):
  for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
    for f in filenames:
      if f.lower().endswith(tuple(exts)):
        yield Path(dirpath) / f


def paths_from_list(list_file, root):
  found = []
  for row in csv.reader(io.StringIO(read(list_file))):
    for cell in row:
      cell = cell.strip().strip('"').replace('\\', '/')
      if cell.lower().endswith(UNIT_EXTS):
        p = Path(cell)
        found.append(p if p.is_absolute() else root / p)
  return found


def tobe_traces(root):
  keys = set()
  for path in walk(root, TOBE_EXTS):
    text = read(path)
    if 'AS-IS:' in text:
      keys |= {m.group(1).rstrip('->*/') for m in TRACE.finditer(text)}
  return keys


def spec_status(skill, path, method=None):
  p = spec_path(skill, path, method)
  if not p.is_file():
    return '없음'
  return '검토 완료' if SPEC_DONE.search(read(p)) else '검토 전'


def arg(p):
  return f'"{p}"' if ' ' in str(p) else str(p)


def main(argv=None):
  ap = argparse.ArgumentParser(description='AS-IS 변환 단위·매핑 누락 사전 점검')
  ap.add_argument('--list', action='append', default=[])
  ap.add_argument('--asis-root', default='.')
  ap.add_argument('--scan')
  ap.add_argument('--tobe', default=str(PROJECT))
  ap.add_argument('--out', default=str(PROJECT / 'docs' / 'inventory'))
  args = ap.parse_args(argv)
  if not args.list and not args.scan:
    ap.error('--list 또는 --scan 이 필요함')

  root = Path(args.asis_root)
  paths = [p for f in args.list for p in paths_from_list(f, root)]
  if args.scan:
    paths += list(walk(args.scan, UNIT_EXTS))
  paths = sorted({p.resolve() for p in paths})
  missing = [p for p in paths if not p.is_file()]
  paths = [p for p in paths if p.is_file()]

  tables = rows('tables.csv')
  mapped = {r['asis_table'].upper() for r in tables}
  dropped = {r['asis_table'].upper() for r in tables if r['status'].strip().upper() == 'DROPPED'}
  rfcs = {r['rfc_function'] for r in rows('sap.csv')}
  traces = tobe_traces(args.tobe)

  units, gaps = [], defaultdict(list)
  for p in paths:
    text = read(p)
    ext = p.suffix.lower()
    if ext == '.xml' and '<sqlMap' in text:
      for kind, sid in STATEMENT.findall(text):
        key = unit_key(p, sid)
        used = sql_tables(extract_statement(text, sid) or '')
        miss = sorted(used - mapped)
        for t in miss:
          gaps[('미매핑 테이블', t)].append(key)
        for t in sorted(used & dropped):
          gaps[('폐기 테이블 사용', t)].append(key)
        done = key in traces
        step = '완료' if done else '(매핑 먼저)' if miss else f'/convert-query {arg(p)} {sid} <TO-BE mapper.xml>'
        units.append(['query', key, p, sid, kind, ' '.join(sorted(used)), ' '.join(miss), '-',
                      '완료' if done else '', step])
    elif ext == '.java':
      for name in RFC_CALL.findall(text):
        if name not in rfcs:
          gaps[('미매핑 RFC', name)].append(unit_key(p))
      for name in dict.fromkeys(PUBLIC_METHOD.findall(text)):
        if SKIP_METHOD.match(name):
          continue
        key = unit_key(p, name)
        spec = spec_status('spec-logic', p, name)
        done = key in traces
        step = ('완료' if done else f'/spec-logic {arg(p)} {name}' if spec == '없음'
                else '(명세 검토)' if spec == '검토 전' else f'/convert-logic {arg(p)} {name}')
        units.append(['logic', key, p, name, '', '', '', spec, '완료' if done else '', step])
    elif ext == '.jsp':
      key = unit_key(p)
      spec = spec_status('spec-screen', p)
      parts = [x for x in SCREEN_PARTS if f'{key}#{x}' in traces]
      todo = [x for x in SCREEN_PARTS if x not in parts]
      step = ('완료' if not todo else f'/spec-screen {arg(p)}' if spec == '없음'
              else '(명세 검토)' if spec == '검토 전' else f'/convert-screen {arg(p)} {todo[0]}')
      units.append(['screen', key, p, '', '', '', '', spec, ','.join(parts), step])

  out = Path(args.out)
  out.mkdir(parents=True, exist_ok=True)
  with open(out / 'units.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['유형', '키', 'AS-IS 경로', '대상', '종류', '사용 테이블', '매핑 누락 테이블', '명세', '변환', '다음 단계'])
    w.writerows(units)
  ranked = sorted(gaps.items(), key=lambda kv: (-len(kv[1]), kv[0]))
  with open(out / 'mapping-gaps.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['종류', '이름', '사용 횟수', '사용처 (최대 5)'])
    w.writerows([kind, name, len(where), ' '.join(list(dict.fromkeys(where))[:5])] for (kind, name), where in ranked)

  # 요약
  by_type = Counter(u[0] for u in units)
  steps = Counter('완료' if u[9] == '완료' else u[9] if u[9].startswith('(') else '실행 가능' for u in units)
  dup = [k for k, n in Counter(u[1] for u in units).items() if n > 1]
  print(f'AS-IS 파일 {len(paths)}개' + (f' (목록에 있으나 없는 파일 {len(missing)}개, 예: {missing[0]})' if missing else ''))
  print('변환 단위: ' + ', '.join(f'{t} {by_type[t]}' for t in ('query', 'logic', 'screen')))
  print('진행: ' + ', '.join(f'{k} {v}' for k, v in steps.most_common()))
  print('매핑 누락: ' + (', '.join(f'{k} {v}종' for k, v in Counter(k for k, _ in gaps).items()) or '없음'))
  for (kind, name), where in ranked[:10]:
    print(f'  {kind:10} {name:30} {len(where)}건')
  if dup:
    print(f'⚠ 키 중복 {len(dup)}개 (상위폴더/파일명이 같은 파일) — 변환 상태가 섞일 수 있음. 예: {dup[0]}')
  print(f'결과: {out / "units.csv"}, {out / "mapping-gaps.csv"}')


if __name__ == '__main__':
  main()
