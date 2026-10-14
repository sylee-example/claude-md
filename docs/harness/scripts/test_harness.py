#!/usr/bin/env python3
"""brief.py / check.py 자체 검증. 실행: python3 docs/harness/scripts/test_harness.py"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brief  # noqa: E402
import check  # noqa: E402

TABLES = '''asis_table,tobe_table,status,merge_cond,note
TB_CUST_M,CM_CUSTOMER,RENAMED,,
TB_CUST_CORP,CM_CUSTOMER,MERGED,CUST_TYPE_CD = 'CORP',
'''
COLUMNS = '''asis_table,asis_column,tobe_table,tobe_column,rule
TB_CUST_M,CUST_NO,CM_CUSTOMER,CUSTOMER_ID,
TB_CUST_M,REG_DT,CM_CUSTOMER,CREATED_AT,TO_DATE
TB_CUST_M,NAME,CM_CUSTOMER,CUSTOMER_NAME,
TB_ORDER,CUST_NO,CM_ORDER,ORDER_CUSTOMER_ID,
'''
SAP = '''rfc_function,rfc_param,rap_path,rap_field,method,note
Z_SD_GET_ORDER,,/sap/x/SalesOrder,,GET,
'''
SQLMAP = '''<sqlMap namespace="Cust">
  <resultMap id="custMap" class="java.util.HashMap">
    <result property="custNo" column="CUST_NO"/>
  </resultMap>
  <sql id="baseCols">A.CUST_NO, A.REG_DT</sql>
  <select id="selectOther" resultClass="java.util.HashMap">SELECT 1 FROM TB_OTHER_ONLY</select>
  <select id="selectCust" parameterClass="java.util.HashMap" resultMap="custMap">
    SELECT <include refid="Cust.baseCols"/>, EXTRACT(YEAR FROM SYSDATE)
      FROM TB_CUST_M A, TB_CUST_CORP B, TB_UNKNOWN C
    <dynamic prepend="WHERE">
      <isNotEmpty property="custNo" prepend="AND">A.CUST_NO = #custNo#</isNotEmpty>
    </dynamic>
  </select>
</sqlMap>
'''
JAVA = '''public class CustBiz {
  public void other() {
    if (helper.selectCust(a)) { x(); }
  }
  public List selectCust(Map param) throws Exception {
    if (param != null) {
      return sqlMapClient.queryForList("Cust.selectCust", param);
    }
    return null;
  }
  public void after() {}
}
'''


class HarnessTest(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.root = Path(self.tmp.name)
    mapping = self.root / 'mapping'
    mapping.mkdir()
    (mapping / 'tables.csv').write_text(TABLES, encoding='utf-8')
    (mapping / 'columns.csv').write_text(COLUMNS, encoding='utf-8')
    (mapping / 'sap.csv').write_text(SAP, encoding='utf-8')
    self._orig = check.MAPPING
    check.MAPPING = mapping

  def tearDown(self):
    check.MAPPING = self._orig
    self.tmp.cleanup()

  def write(self, rel, text, encoding='utf-8'):
    path = self.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return str(path)

  def run_brief(self, *args):
    out = io.StringIO()
    sys.argv = ['brief.py', *args]
    with contextlib.redirect_stdout(out):
      try:
        brief.main()
      except SystemExit:
        pass
    return out.getvalue()

  # ---- brief.py ----
  def test_query_brief_extracts_only_target_with_fragments(self):
    out = self.run_brief('query', self.write('Cust.xml', SQLMAP), 'selectCust')
    self.assertIn('<select id="selectCust"', out)
    self.assertNotIn('TB_OTHER_ONLY', out)          # 다른 statement 제외
    self.assertIn('<sql id="baseCols">', out)        # include 조각 포함
    self.assertIn('<resultMap id="custMap"', out)    # resultMap 포함
    self.assertIn('| TB_CUST_CORP | CM_CUSTOMER | MERGED |', out)
    self.assertIn('CUSTOMER_ID | customerId', out)
    self.assertNotIn('ORDER_CUSTOMER_ID', out)       # 쿼리에 없는 테이블의 동명 컬럼 제외
    self.assertIn('매핑 없는 테이블: TB_UNKNOWN', out)  # SYSDATE 는 테이블로 안 봄
    self.assertIn('## [query] iBatis 2 → MyBatis 3', out)
    self.assertNotIn('[screen]', out)

  def test_query_brief_missing_id_stops(self):
    out = self.run_brief('query', self.write('Cust.xml', SQLMAP), 'nope')
    self.assertIn('작업지시서 생성 실패', out)

  def test_logic_brief_extracts_declaration_not_call_site(self):
    out = self.run_brief('logic', self.write('CustBiz.java', JAVA), 'selectCust')
    self.assertIn('public List selectCust(Map param)', out)
    self.assertIn('return null;', out)
    self.assertNotIn('helper.selectCust(a)', out)
    self.assertNotIn('after()', out)

  def test_cp949_source_is_readable(self):
    path = self.write('Legacy.java', '// 고객 조회\n' + JAVA, encoding='cp949')
    out = self.run_brief('logic', path, 'selectCust')
    self.assertIn('public List selectCust', out)

  def test_screen_brief_attaches_files(self):
    jsp = self.write('cust.jsp', '<script>grid.setColumn("custNo"); Z_SD_GET_ORDER</script>')
    js = self.write('cust.js', 'function search(){}')
    out = self.run_brief('screen', jsp, js)
    self.assertIn('customerId', out)                 # camel 로 등장해도 매핑 찾음
    self.assertIn('/sap/x/SalesOrder', out)
    self.assertIn('function search(){}', out)

  # ---- check.py ----
  def test_ibatis_remnants_flagged(self):
    errors = check.check_file(self.write('out/CustMapper.xml', SQLMAP))
    text = '\n'.join(errors)
    for word in ('sqlMap', 'parameterClass', 'resultClass', '동적 태그', '<dynamic>', '#param#', 'AS-IS 이름 잔존'):
      self.assertIn(word, text)

  def test_clean_mybatis_passes(self):
    xml = '''<mapper namespace="a.CustomerMapper">
  <select id="selectCust" parameterType="a.Req" resultType="a.Res">
    SELECT A.CUSTOMER_ID, A.CUSTOMER_NAME FROM CM_CUSTOMER A
    <where><if test='customerId != null and customerId != ""'>AND A.CUSTOMER_ID = #{customerId}</if></where>
    -- TODO(HARNESS): 매핑 없음 TB_UNKNOWN
    -- AS-IS: TB_CUST_M.CUST_NO
  </select>
</mapper>'''
    self.assertEqual(check.check_file(self.write('out/CustomerMapper.xml', xml)), [])

  def test_single_word_old_name_not_flagged(self):
    self.assertEqual(check.check_file(self.write('src/shared/lib/a.ts', 'const name: string = "x"\n')), [])

  def test_java_rules(self):
    java = 'import javax.servlet.http.HttpServletRequest;\n@Autowired\nprivate X x;\nString custNo;\n'
    text = '\n'.join(check.check_file(self.write('A.java', java)))
    self.assertIn('jakarta', text)
    self.assertIn('생성자 주입', text)
    self.assertIn("['custNo']", text)

  def test_ts_rules_and_fsd(self):
    src = 'src/features/cust-search/ui/Form.tsx'
    ok = ("import { Button } from 'antd'\n"
          "import { useCustomerQuery } from '@/entities/customer'\n"
          "import { Field } from '../model/types'\n"
          "Modal.confirm({})\n"
          "const a: unknown = 1\n")
    self.assertEqual(check.check_file(self.write(src, ok)), [])
    bad = ("import { Page } from '@/pages/cust'\n"
           "import { X } from '../../order-search/ui/X'\n"
           "const a: any = 1\n"
           "alert('x')\n")
    text = '\n'.join(check.check_file(self.write(src, bad)))
    self.assertIn('상위 레이어 pages', text)
    self.assertIn('다른 슬라이스', text)
    self.assertIn('any 금지', text)
    self.assertIn('alert/confirm', text)

  def test_hook_mode_exit_2(self):
    path = self.write('out/B.xml', '<select id="a" resultClass="x">SELECT 1 FROM DUAL</select>')
    res = subprocess.run([sys.executable, str(HERE / 'check.py')], input=json.dumps({'tool_input': {'file_path': path}}),
                         capture_output=True, text=True)
    self.assertEqual(res.returncode, 2)
    self.assertIn('resultClass → resultType', res.stderr)
    res = subprocess.run([sys.executable, str(HERE / 'check.py')], input=json.dumps({'tool_input': {'file_path': 'a.md'}}),
                         capture_output=True, text=True)
    self.assertEqual(res.returncode, 0)


if __name__ == '__main__':
  unittest.main()
