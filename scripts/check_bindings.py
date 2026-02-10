import os, json, re
base = os.path.join(os.path.dirname(__file__), '..', 'hf-space-inventory-sqlgen')
base = os.path.abspath(base)
SCHEMA_DIR = os.path.join(base, 'app_schema')
QUERIES_DIR = os.path.join(SCHEMA_DIR, 'queries')
GROUND_TRUTH_DIR = os.path.join(SCHEMA_DIR, 'ground_truth')
GROUND_TRUTH_SQL_DIR = os.path.join(GROUND_TRUTH_DIR, 'sql_snippets')
MANIFEST_PATH = os.path.join(GROUND_TRUTH_DIR, 'reviewer_manifest.json')


def normalize_sql(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"--.*?\n", "\n", s)
    s = re.sub(r"--.*$", "", s, flags=re.M)
    s = s.replace(';',' ')
    s = " ".join(s.split())
    return s.lower().strip()

manifest = {}
if os.path.exists(MANIFEST_PATH):
    try:
        with open(MANIFEST_PATH,'r') as f:
            manifest = json.load(f)
    except Exception as e:
        print('manifest load error', e)

approved = manifest.get('approved_snippets', {})
print('approved snippets:', len(approved))

for fn in sorted(os.listdir(QUERIES_DIR)):
    if not fn.endswith('.sql'):
        continue
    path = os.path.join(QUERIES_DIR, fn)
    print('\n== QUERY FILE:', fn)
    with open(path,'r') as f:
        content = f.read()
    lines = content.split('\n')
    current = {'name':'','description':'','sql':''}
    def process_current(cur):
        if not cur['sql'].strip():
            return
        qname=cur['name']
        qsql=cur['sql']
        qnorm=normalize_sql(qsql)
        matched=False
        for binding_key, entry in approved.items():
            file_path=entry.get('file_path','')
            if not file_path or not os.path.exists(file_path):
                candidate=os.path.join(GROUND_TRUTH_SQL_DIR,f"{binding_key}.sql")
                if os.path.exists(candidate):
                    file_path=candidate
                else:
                    continue
            try:
                with open(file_path,'r') as sf:
                    snippet=sf.read()
            except Exception:
                continue
            if normalize_sql(snippet)==qnorm:
                print(f"MATCH: query '{qname}' -> {binding_key}.sql (file: {file_path})")
                matched=True
                break
        if not matched:
            print(f"NO MATCH: query '{qname}'")
    for line in lines:
        if line.startswith('-- Query:'):
            process_current(current)
            current={'name':line.replace('-- Query:','').strip(),'description':'','sql':''}
        elif line.startswith('-- Description:'):
            current['description']=line.replace('-- Description:','').strip()
        elif not line.startswith('-- ') and line.strip():
            current['sql']+=line+"\n"
    process_current(current)

print('\nDone')
