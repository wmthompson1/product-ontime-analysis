LOOSE ENDS (branch: wip_20251004)

Summary:
- Purpose: collect remaining cleanup tasks and verification steps after the history-scrub and local-dev conversion.

Confirmed completed items:
- Root  and Python venv scaffolding implemented.
-  updated to ignore  variants.
-  scrubbed from history and cleaned on remote  (force-push completed).
-  removed to resolve Astro peer-dependency conflict.

Remaining tasks / recommendations:
- Verify no sensitive secrets remain on remote.
- Delete or sanitize sample files that contain real connection strings (e.g., ).
- Ensure local  files are kept out of commits; use Replit / CI secrets for deployments.
- Confirm  is in the desired location and integrated into any DB tooling.
- Optionally remove any other  files (e.g., ) or replace them with placeholder-only templates.

Files I recommend reviewing (contain environment-variable references or sample secrets):
- 
- 
- 
- 
- 
-  and files under  that reference  or 

Commands for verification (run locally):
- Search for common secret prefixes:
  - 001_Entry_Point_Kane_Ragas.py:77:        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
004_Entry_Point_Kane_Complete_RAG.py:98:        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
005_Entry_Point_Kane_LangSmith.py:204:        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
008_Entry_Point_Acad_LC_Start1.py:12:        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
010_Entry_Point_Custom_Tools.py:310:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
011_Entry_Point_LangGraph_Base.py:164:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
012_Entry_Point_StateGraph_Pattern.py:152:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
013_Entry_Point_Manufacturing_Assistant.py:272:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
014_Entry_Point_Official_Manufacturing_Assistant.py:259:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
015_Entry_Point_Manufacturing_Queue_Router.py:202:        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
016_Entry_Point_Manufacturing_Configuration.py:129:            openai_api_key=os.getenv("OPENAI_API_KEY"),
016_Entry_Point_Manufacturing_Configuration.py:147:            openai_api_key=os.getenv("OPENAI_API_KEY"),
016_Entry_Point_Manufacturing_Configuration.py:167:            openai_api_key=os.getenv("OPENAI_API_KEY"),
016_Entry_Point_Manufacturing_Configuration.py:206:            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
01william/sample.txt:3:postgresql://neondb_owner:npg_YXlh7Qe9qopC@ep-restless-mode-a550obx6.us-east-2.aws.neon.tech/neondb?sslmode=require
01william/sample.txt:5:neondb
01william/sample.txt:7:ep-restless-mode-a550obx6.us-east-2.aws.neon.tech
01william/sample.txt:11:neondb_owner
104AIwork.py:14:client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEVELOPMENT.md:118:- `OPENAI_API_KEY` — your OpenAI API key
Entry_Point_001_few_shot.py:169:        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
LangChain_Academy_Setup_Guide.md:44:OPENAI_API_KEY=your_openai_api_key
Local_Installation_Guide.md:73:pip install flask flask-sqlalchemy psycopg2-binary sqlalchemy requests beautifulsoup4 lxml trafilatura
Replit NPM advisory.md:9:   - OPENAI_API_KEY
app/huggingface_mcp.py:311:def create_hf_mcp_client() -> Optional[HuggingFaceMCPClient]:
app/huggingface_mcp.py:325:    client = create_hf_mcp_client()
app/main.py:312:                "openai_api_configured": bool(os.getenv("OPENAI_API_KEY")),
app/semantic_layer.py:66:        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
astro-framework-explanation.md:18:- **Flask Integration** (`/flask-integration`): Live API connection testing
astro-framework-explanation.md:85:1. **Flask-like Simplicity**: Start minimal, add features as needed
astro-sample/package-lock.json:4025:        "mdast-util-gfm-task-list-item": "^2.0.0",
astro-sample/package-lock.json:4099:    "node_modules/mdast-util-gfm-task-list-item": {
astro-sample/package-lock.json:4101:      "resolved": "https://registry.npmjs.org/mdast-util-gfm-task-list-item/-/mdast-util-gfm-task-list-item-2.0.0.tgz",
astro-sample/package-lock.json:4273:        "micromark-extension-gfm-task-list-item": "^2.0.0",
astro-sample/package-lock.json:4366:    "node_modules/micromark-extension-gfm-task-list-item": {
astro-sample/package-lock.json:4368:      "resolved": "https://registry.npmjs.org/micromark-extension-gfm-task-list-item/-/micromark-extension-gfm-task-list-item-2.1.0.tgz",
astro-sample/package-lock.json:5355:      "resolved": "https://registry.npmjs.org/queue-microtask/-/queue-microtask-1.2.3.tgz",
astro-sample/src/layouts/Layout.astro:28:            <a href="/flask-integration" class="text-gray-600 hover:text-blue-600">Flask Integration</a>
debug_sql_generation.py:59:        openai_key = os.getenv('OPENAI_API_KEY')
docs/local-postgres-setup.md:76:# DATABASE_URL=postgresql+psycopg2://user:pass@host.neon.tech:5432/dbname?sslmode=require
docs/local-postgres-setup.md:79:OPENAI_API_KEY=sk-...
docs/local-postgres-setup.md:80:TAVILY_API_KEY=tvly-...
docs/local-postgres-setup.md:81:HUGGINGFACE_TOKEN=hf_...
docs/local-postgres-setup.md:90:| Neon/Replit | `postgresql+psycopg2://user:pass@host.neon.tech:5432/dbname?sslmode=require` | Yes |
docs/local-postgres-setup.md:120:# Install Flask-Migrate (already in requirements.txt)
docs/local-postgres-setup.md:121:pip install flask-migrate
docs/local-postgres-setup.md:310:> "Set up Flask-Migrate and create an initial migration for my SQLAlchemy models"
flask_primer.md:373:Flask-SQLAlchemy==3.0.5
flask_primer.md:381:- Explore **Flask extensions** (Flask-Login, Flask-Mail, Flask-Admin)
flask_primer.md:382:- Study **API development** with Flask-RESTful
flask_primer.md:388:- Flask Mega-Tutorial: https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world
hello-astro/package-lock.json:2705:        "mdast-util-gfm-task-list-item": "^2.0.0",
hello-astro/package-lock.json:2779:    "node_modules/mdast-util-gfm-task-list-item": {
hello-astro/package-lock.json:2781:      "resolved": "https://registry.npmjs.org/mdast-util-gfm-task-list-item/-/mdast-util-gfm-task-list-item-2.0.0.tgz",
hello-astro/package-lock.json:2950:        "micromark-extension-gfm-task-list-item": "^2.0.0",
hello-astro/package-lock.json:3043:    "node_modules/micromark-extension-gfm-task-list-item": {
hello-astro/package-lock.json:3045:      "resolved": "https://registry.npmjs.org/micromark-extension-gfm-task-list-item/-/micromark-extension-gfm-task-list-item-2.1.0.tgz",
hf-mcp-http.log:11:{"level":30,"time":"2025-12-01T20:31:49.264Z","pid":87839,"hostname":"Williams-MacBook-Pro.local","msg":"Tool hf_doc_fetch state changed: true -> false"}
hf-mcp-http.log:13:{"level":30,"time":"2025-12-01T20:31:49.264Z","pid":87839,"hostname":"Williams-MacBook-Pro.local","msg":"Tool hf_jobs state changed: true -> false"}
javascript_framework_guide.md:83:### 2. Project Structure (Flask-like)
langchain-agents-from-scratch/.env.example:1:OPENAI_API_KEY=your_openai_api_key
langchain-agents-from-scratch/README.md:37:OPENAI_API_KEY=your_openai_api_key
langchain-agents-from-scratch/README.md:44:export OPENAI_API_KEY=your_openai_api_key
langchain-agents-from-scratch/src/email_assistant/tools/gmail/README.md:114:   * `OPENAI_API_KEY`
main.py:1678:    from app.huggingface_mcp import create_hf_mcp_client
main.py:1690:        client = create_hf_mcp_client()
main.py:1715:    from app.huggingface_mcp import create_hf_mcp_client
main.py:1718:        client = create_hf_mcp_client()
main.py:1736:    from app.huggingface_mcp import create_hf_mcp_client
main.py:1739:        client = create_hf_mcp_client()
mcp_server/.env.example:7:OPENAI_API_KEY=
pyproject.toml:9:    "flask-migrate>=4.1.0",
pyproject.toml:10:    "flask-sqlalchemy>=3.1.1",
replit.md:19:- **ORM**: SQLAlchemy with Flask-SQLAlchemy
replit.md:82:- **Flask-SQLAlchemy**: ORM integration for Flask
requirements.txt:4:flask-migrate>=4.1.0
requirements.txt:5:flask-sqlalchemy>=3.1.1
schema/schema.sql:39:-- Name: corrective_actions; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:56:-- Name: corrective_actions_capa_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:70:-- Name: corrective_actions_capa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:77:-- Name: daily_deliveries; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:94:-- Name: daily_deliveries_delivery_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:108:-- Name: daily_deliveries_delivery_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:115:-- Name: downtime_events; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:138:-- Name: downtime_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:152:-- Name: downtime_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:159:-- Name: effectiveness_metrics; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:180:-- Name: effectiveness_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:194:-- Name: effectiveness_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:201:-- Name: equipment_metrics; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:221:-- Name: equipment_metrics_equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:235:-- Name: equipment_metrics_equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:242:-- Name: equipment_reliability; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:260:-- Name: equipment_reliability_reliability_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:274:-- Name: equipment_reliability_reliability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:281:-- Name: failure_events; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:305:-- Name: failure_events_failure_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:319:-- Name: failure_events_failure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:326:-- Name: financial_impact; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:349:-- Name: financial_impact_impact_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:363:-- Name: financial_impact_impact_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:370:-- Name: industry_benchmarks; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:388:-- Name: industry_benchmarks_benchmark_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:402:-- Name: industry_benchmarks_benchmark_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:409:-- Name: maintenance_targets; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:428:-- Name: maintenance_targets_target_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:442:-- Name: maintenance_targets_target_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:449:-- Name: manufacturing_acronyms; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:465:-- Name: manufacturing_acronyms_acronym_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:479:-- Name: manufacturing_acronyms_acronym_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:486:-- Name: non_conformant_materials; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:507:-- Name: non_conformant_materials_ncm_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:521:-- Name: non_conformant_materials_ncm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:528:-- Name: product_defects; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:547:-- Name: product_defects_defect_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:561:-- Name: product_defects_defect_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:568:-- Name: product_lines; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:589:-- Name: product_lines_product_line_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:603:-- Name: product_lines_product_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:610:-- Name: production_lines; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:631:-- Name: production_lines_line_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:645:-- Name: production_lines_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:652:-- Name: production_quality; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:670:-- Name: production_quality_quality_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:684:-- Name: production_quality_quality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:691:-- Name: production_schedule; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:711:-- Name: production_schedule_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:725:-- Name: production_schedule_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:732:-- Name: products; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:744:-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:758:-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:765:-- Name: quality_costs; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:786:-- Name: quality_costs_cost_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:800:-- Name: quality_costs_cost_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:807:-- Name: quality_incidents; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:829:-- Name: quality_incidents_incident_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:843:-- Name: quality_incidents_incident_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:850:-- Name: schema_edges; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:870:-- Name: schema_edges_edge_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:884:-- Name: schema_edges_edge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:891:-- Name: schema_nodes; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:904:-- Name: suppliers; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:921:-- Name: suppliers_supplier_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:935:-- Name: suppliers_supplier_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:942:-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
schema/schema.sql:954:-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
schema/schema.sql:968:-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
schema/schema.sql:975:-- Name: corrective_actions capa_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:982:-- Name: daily_deliveries delivery_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:989:-- Name: downtime_events event_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:996:-- Name: effectiveness_metrics metric_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1003:-- Name: equipment_metrics equipment_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1010:-- Name: equipment_reliability reliability_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1017:-- Name: failure_events failure_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1024:-- Name: financial_impact impact_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1031:-- Name: industry_benchmarks benchmark_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1038:-- Name: maintenance_targets target_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1045:-- Name: manufacturing_acronyms acronym_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1052:-- Name: non_conformant_materials ncm_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1059:-- Name: product_defects defect_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1066:-- Name: product_lines product_line_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1073:-- Name: production_lines line_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1080:-- Name: production_quality quality_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1087:-- Name: production_schedule schedule_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1094:-- Name: products id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1101:-- Name: quality_costs cost_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1108:-- Name: quality_incidents incident_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1115:-- Name: schema_edges edge_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1122:-- Name: suppliers supplier_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1129:-- Name: users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
schema/schema.sql:1136:-- Name: corrective_actions corrective_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1144:-- Name: daily_deliveries daily_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1152:-- Name: downtime_events downtime_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1160:-- Name: effectiveness_metrics effectiveness_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1168:-- Name: equipment_metrics equipment_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1176:-- Name: equipment_reliability equipment_reliability_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1184:-- Name: failure_events failure_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1192:-- Name: financial_impact financial_impact_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1200:-- Name: industry_benchmarks industry_benchmarks_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1208:-- Name: maintenance_targets maintenance_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1216:-- Name: manufacturing_acronyms manufacturing_acronyms_acronym_table_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1224:-- Name: manufacturing_acronyms manufacturing_acronyms_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1232:-- Name: non_conformant_materials non_conformant_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1240:-- Name: product_defects product_defects_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1248:-- Name: product_lines product_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1256:-- Name: production_lines production_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1264:-- Name: production_quality production_quality_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1272:-- Name: production_schedule production_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1280:-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1288:-- Name: quality_costs quality_costs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1296:-- Name: quality_incidents quality_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1304:-- Name: schema_edges schema_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1312:-- Name: schema_nodes schema_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1320:-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1328:-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1336:-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1344:-- Name: idx_acronym; Type: INDEX; Schema: public; Owner: neondb_owner
schema/schema.sql:1351:-- Name: idx_table_name; Type: INDEX; Schema: public; Owner: neondb_owner
schema/schema.sql:1358:-- Name: corrective_actions corrective_actions_ncm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1366:-- Name: daily_deliveries daily_deliveries_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1374:-- Name: downtime_events downtime_events_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1382:-- Name: equipment_reliability equipment_reliability_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1390:-- Name: manufacturing_acronyms manufacturing_acronyms_table_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1398:-- Name: non_conformant_materials non_conformant_materials_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1406:-- Name: quality_costs quality_costs_product_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1414:-- Name: schema_edges schema_edges_from_table_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1422:-- Name: schema_edges schema_edges_to_table_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
schema/schema.sql:1433:ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;
schema/schema.sql:1440:ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;
semantic_layer_ver1.py:21:openai.api_key = os.getenv("OPENAI_API_KEY")
semantic_layer_ver2.py:21:openai.api_key = os.getenv("OPENAI_API_KEY")
semantic_layer_ver3.py:21:api_key = os.getenv("OPENAI_API_KEY")
semantic_layer_ver3.py:84:# api_key = userdata.get('OPENAI_API_KEY')
semantic_layer_ver3.py:85:client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
semantics_merge.py:29:api_key = os.getenv("OPENAI_API_KEY")
semantics_merge.py:30:# api_key = os.getenv("OPENAI_API_KEY")
semantics_merge.py:33:        'WARNING: OPENAI_API_KEY not set. Set it in a .env file or environment variables.'
setup_local.py:23:        "Flask-SQLAlchemy==3.1.1", 
setup_local.py:30:        "Flask-Migrate==4.0.5"
test_entry_points.py:211:        original_openai_key = os.environ.get('OPENAI_API_KEY')
test_entry_points.py:212:        if 'OPENAI_API_KEY' in os.environ:
test_entry_points.py:213:            del os.environ['OPENAI_API_KEY']
test_entry_points.py:228:                os.environ['OPENAI_API_KEY'] = original_openai_key
test_langchain_academy.py:39:        env_vars = ["OPENAI_API_KEY", "LANGSMITH_PROJECT"]
uv.lock:217:sdist = { url = "https://files.pythonhosted.org/packages/c0/de/e47735752347f4128bcf354e0da07ef311a78244eba9e3dc1d4a5ab21a98/flask-3.1.1.tar.gz", hash = "sha256:284c7b8f2f58cb737f0cf1c30fd7eaf0ccfcde196099d24ecede3fc2005aa59e", size = 753440, upload-time = "2025-05-13T15:01:17.447Z" }
uv.lock:219:    { url = "https://files.pythonhosted.org/packages/3d/68/9d4508e893976286d2ead7f8f571314af6c2037af34853a30fd769c02e9d/flask-3.1.1-py3-none-any.whl", hash = "sha256:07aae2bb5eaf77993ef57e357491839f5fd9f4dc281593a81a9e4d79a24f295c", size = 103305, upload-time = "2025-05-13T15:01:15.591Z" },
uv.lock:223:name = "flask-migrate"
uv.lock:229:    { name = "flask-sqlalchemy" },
uv.lock:237:name = "flask-sqlalchemy"
uv.lock:1039:    { name = "flask-migrate" },
uv.lock:1040:    { name = "flask-sqlalchemy" },
uv.lock:1055:    { name = "flask-migrate", specifier = ">=4.1.0" },
uv.lock:1056:    { name = "flask-sqlalchemy", specifier = ">=3.1.1" },
- Resynchronize local clones after history rewrite:
  - Your branch is ahead of 'origin/main' by 1 commit.
  (use "git push" to publish your local commits)
HEAD is now at d5ec480 chore(secrets): remove embedded secrets from .env.example; ignore local env variants

Notes for collaborators:
- Because history was rewritten, forks and clones must reset as above before pushing.
- If you see push rejections from GitHub secret scanning after changes, do not attempt to push sensitive values — rotate any exposed keys immediately.

If you'd like, I can:
- Sanitize  and any other files that contain real credentials (I will replace values with placeholders).
- Run a repository-wide secret scan and produce a CSV of matches.
- Finalize deletion of any remaining  files from HEAD.
