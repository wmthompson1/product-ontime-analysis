--
-- PostgreSQL database dump
--


-- Dumped from database version 16.11 (b740647)
-- Dumped by pg_dump version 16.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: corrective_actions; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.corrective_actions (
    capa_id integer NOT NULL,
    ncm_id integer,
    action_description text,
    target_date date,
    actual_date date,
    effectiveness_score numeric(3,2),
    status character varying(50),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: corrective_actions_capa_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.corrective_actions_capa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: corrective_actions_capa_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.corrective_actions_capa_id_seq OWNED BY public.corrective_actions.capa_id;


--
-- Name: daily_deliveries; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.daily_deliveries (
    delivery_id integer NOT NULL,
    supplier_id integer,
    delivery_date date NOT NULL,
    planned_quantity integer,
    actual_quantity integer,
    ontime_rate numeric(5,4),
    quality_score numeric(3,2),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: daily_deliveries_delivery_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.daily_deliveries_delivery_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: daily_deliveries_delivery_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.daily_deliveries_delivery_id_seq OWNED BY public.daily_deliveries.delivery_id;


--
-- Name: downtime_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.downtime_events (
    event_id integer NOT NULL,
    line_id integer,
    equipment_id integer,
    event_start_time timestamp without time zone NOT NULL,
    event_end_time timestamp without time zone,
    downtime_duration_minutes integer,
    downtime_category character varying(100) NOT NULL,
    downtime_reason character varying(200),
    impact_severity character varying(50),
    production_loss_units integer,
    cost_impact numeric(12,2),
    resolution_method text,
    reported_by character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: downtime_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.downtime_events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: downtime_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.downtime_events_event_id_seq OWNED BY public.downtime_events.event_id;


--
-- Name: effectiveness_metrics; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.effectiveness_metrics (
    metric_id integer NOT NULL,
    measurement_date date NOT NULL,
    metric_type character varying(100) NOT NULL,
    metric_value numeric(10,6) NOT NULL,
    target_value numeric(10,6),
    variance_percentage numeric(8,4),
    measurement_unit character varying(50),
    department character varying(100),
    measurement_method character varying(100),
    confidence_level numeric(5,4),
    data_source character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: effectiveness_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.effectiveness_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: effectiveness_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.effectiveness_metrics_metric_id_seq OWNED BY public.effectiveness_metrics.metric_id;


--
-- Name: equipment_metrics; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.equipment_metrics (
    equipment_id integer NOT NULL,
    line_id character varying(50) NOT NULL,
    equipment_type character varying(100),
    equipment_name character varying(255),
    measurement_date date NOT NULL,
    availability_rate numeric(5,4),
    performance_rate numeric(5,4),
    quality_rate numeric(5,4),
    oee_score numeric(5,4),
    downtime_hours numeric(8,2),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: equipment_metrics_equipment_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.equipment_metrics_equipment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: equipment_metrics_equipment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.equipment_metrics_equipment_id_seq OWNED BY public.equipment_metrics.equipment_id;


--
-- Name: equipment_reliability; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.equipment_reliability (
    reliability_id integer NOT NULL,
    equipment_id integer,
    measurement_period date NOT NULL,
    mtbf_hours numeric(10,2),
    target_mtbf numeric(10,2),
    failure_count integer,
    operating_hours numeric(10,2),
    reliability_score numeric(5,4),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: equipment_reliability_reliability_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.equipment_reliability_reliability_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: equipment_reliability_reliability_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.equipment_reliability_reliability_id_seq OWNED BY public.equipment_reliability.reliability_id;


--
-- Name: failure_events; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.failure_events (
    failure_id integer NOT NULL,
    equipment_id integer NOT NULL,
    failure_date timestamp without time zone NOT NULL,
    failure_type character varying(100) NOT NULL,
    failure_mode character varying(200),
    severity_level character varying(50) NOT NULL,
    downtime_hours numeric(8,2),
    repair_cost numeric(12,2),
    parts_replaced text,
    technician_assigned character varying(100),
    failure_description text,
    root_cause_analysis text,
    preventive_action text,
    mtbf_impact numeric(10,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: failure_events_failure_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.failure_events_failure_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: failure_events_failure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.failure_events_failure_id_seq OWNED BY public.failure_events.failure_id;


--
-- Name: financial_impact; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.financial_impact (
    impact_id integer NOT NULL,
    event_date date NOT NULL,
    impact_type character varying(100) NOT NULL,
    impact_category character varying(100),
    gross_impact numeric(15,2) NOT NULL,
    recovery_amount numeric(15,2) DEFAULT 0,
    net_impact numeric(15,2) NOT NULL,
    affected_product_lines integer,
    root_cause_category character varying(100),
    business_unit character varying(100),
    impact_duration_days integer,
    mitigation_cost numeric(12,2),
    lessons_learned text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: financial_impact_impact_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.financial_impact_impact_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: financial_impact_impact_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.financial_impact_impact_id_seq OWNED BY public.financial_impact.impact_id;


--
-- Name: industry_benchmarks; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.industry_benchmarks (
    benchmark_id integer NOT NULL,
    metric_name character varying(100) NOT NULL,
    industry_sector character varying(100),
    benchmark_value numeric(10,6),
    measurement_unit character varying(50),
    benchmark_class character varying(50),
    last_updated date,
    source character varying(200),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: industry_benchmarks_benchmark_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.industry_benchmarks_benchmark_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: industry_benchmarks_benchmark_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.industry_benchmarks_benchmark_id_seq OWNED BY public.industry_benchmarks.benchmark_id;


--
-- Name: maintenance_targets; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.maintenance_targets (
    target_id integer NOT NULL,
    equipment_type character varying(100) NOT NULL,
    target_mtbf numeric(10,2),
    target_availability numeric(5,4),
    target_reliability numeric(5,4),
    maintenance_interval_hours integer,
    industry_sector character varying(100),
    target_class character varying(50),
    last_updated date DEFAULT CURRENT_DATE,
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: maintenance_targets_target_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.maintenance_targets_target_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: maintenance_targets_target_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.maintenance_targets_target_id_seq OWNED BY public.maintenance_targets.target_id;


--
-- Name: manufacturing_acronyms; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.manufacturing_acronyms (
    acronym_id integer NOT NULL,
    acronym character varying(50) NOT NULL,
    definition text NOT NULL,
    table_name character varying(255),
    category character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: manufacturing_acronyms_acronym_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.manufacturing_acronyms_acronym_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: manufacturing_acronyms_acronym_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.manufacturing_acronyms_acronym_id_seq OWNED BY public.manufacturing_acronyms.acronym_id;


--
-- Name: non_conformant_materials; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.non_conformant_materials (
    ncm_id integer NOT NULL,
    incident_date date NOT NULL,
    product_line character varying(100),
    supplier_id integer,
    material_type character varying(100),
    defect_description text,
    quantity_affected integer,
    severity character varying(50),
    root_cause text,
    cost_impact numeric(10,2),
    status character varying(50),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: non_conformant_materials_ncm_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.non_conformant_materials_ncm_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: non_conformant_materials_ncm_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.non_conformant_materials_ncm_id_seq OWNED BY public.non_conformant_materials.ncm_id;


--
-- Name: product_defects; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.product_defects (
    defect_id integer NOT NULL,
    product_line character varying(100) NOT NULL,
    production_date date NOT NULL,
    defect_type character varying(100),
    defect_count integer,
    total_produced integer,
    defect_rate numeric(6,5),
    severity character varying(50),
    root_cause text,
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: product_defects_defect_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.product_defects_defect_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: product_defects_defect_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.product_defects_defect_id_seq OWNED BY public.product_defects.defect_id;


--
-- Name: product_lines; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.product_lines (
    product_line_id integer NOT NULL,
    product_line_name character varying(100) NOT NULL,
    product_category character varying(100),
    target_volume integer,
    unit_price numeric(10,2),
    profit_margin numeric(5,4),
    launch_date date,
    lifecycle_stage character varying(50),
    primary_market character varying(100),
    complexity_rating character varying(50),
    regulatory_requirements text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: product_lines_product_line_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.product_lines_product_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: product_lines_product_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.product_lines_product_line_id_seq OWNED BY public.product_lines.product_line_id;


--
-- Name: production_lines; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.production_lines (
    line_id integer NOT NULL,
    line_name character varying(100) NOT NULL,
    facility_location character varying(100),
    line_type character varying(50),
    theoretical_capacity integer,
    actual_capacity integer,
    efficiency_rating numeric(5,4),
    installation_date date,
    last_maintenance_date date,
    status character varying(50) DEFAULT 'Active'::character varying,
    supervisor character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: production_lines_line_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.production_lines_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: production_lines_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.production_lines_line_id_seq OWNED BY public.production_lines.line_id;


--
-- Name: production_quality; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.production_quality (
    quality_id integer NOT NULL,
    product_line character varying(100) NOT NULL,
    production_date date NOT NULL,
    defect_rate numeric(6,5),
    total_produced integer,
    defect_count integer,
    shift_id character varying(50),
    line_supervisor character varying(100),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: production_quality_quality_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.production_quality_quality_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: production_quality_quality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.production_quality_quality_id_seq OWNED BY public.production_quality.quality_id;


--
-- Name: production_schedule; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.production_schedule (
    schedule_id integer NOT NULL,
    line_id character varying(50) NOT NULL,
    product_line character varying(100),
    planned_start timestamp without time zone,
    planned_end timestamp without time zone,
    actual_start timestamp without time zone,
    actual_end timestamp without time zone,
    target_quantity integer,
    actual_quantity integer,
    efficiency_score numeric(5,4),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: production_schedule_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.production_schedule_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: production_schedule_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.production_schedule_schedule_id_seq OWNED BY public.production_schedule.schedule_id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.products (
    id integer NOT NULL,
    description text NOT NULL,
    embedding public.vector(384)
);



--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: quality_costs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.quality_costs (
    cost_id integer NOT NULL,
    product_line_id integer,
    cost_date date NOT NULL,
    cost_category character varying(100) NOT NULL,
    cost_subcategory character varying(100),
    cost_amount numeric(12,2) NOT NULL,
    units_affected integer,
    cost_per_unit numeric(10,4),
    cost_driver character varying(200),
    prevention_opportunity text,
    department_charged character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: quality_costs_cost_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.quality_costs_cost_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: quality_costs_cost_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.quality_costs_cost_id_seq OWNED BY public.quality_costs.cost_id;


--
-- Name: quality_incidents; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.quality_incidents (
    incident_id integer NOT NULL,
    product_line character varying(100) NOT NULL,
    incident_date date NOT NULL,
    incident_type character varying(100) NOT NULL,
    severity_level character varying(50) NOT NULL,
    affected_units integer,
    cost_impact numeric(12,2),
    detection_method character varying(100),
    status character varying(50) DEFAULT 'Open'::character varying,
    assigned_to character varying(100),
    resolution_date date,
    root_cause text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: quality_incidents_incident_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.quality_incidents_incident_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: quality_incidents_incident_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.quality_incidents_incident_id_seq OWNED BY public.quality_incidents.incident_id;


--
-- Name: schema_edges; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.schema_edges (
    edge_id integer NOT NULL,
    from_table character varying(255),
    to_table character varying(255),
    relationship_type character varying(100),
    join_column character varying(255),
    weight integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    join_column_description text,
    natural_language_alias character varying(100),
    few_shot_example text,
    context text
);



--
-- Name: schema_edges_edge_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.schema_edges_edge_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: schema_edges_edge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.schema_edges_edge_id_seq OWNED BY public.schema_edges.edge_id;


--
-- Name: schema_nodes; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.schema_nodes (
    table_name character varying(255) NOT NULL,
    table_type character varying(50),
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.suppliers (
    supplier_id integer NOT NULL,
    supplier_name character varying(255) NOT NULL,
    contact_email character varying(255),
    phone character varying(50),
    address text,
    performance_rating numeric(3,2),
    certification_level character varying(100),
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.suppliers_supplier_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.suppliers_supplier_id_seq OWNED BY public.suppliers.supplier_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(120) NOT NULL
);



--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: corrective_actions capa_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.corrective_actions ALTER COLUMN capa_id SET DEFAULT nextval('public.corrective_actions_capa_id_seq'::regclass);


--
-- Name: daily_deliveries delivery_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.daily_deliveries ALTER COLUMN delivery_id SET DEFAULT nextval('public.daily_deliveries_delivery_id_seq'::regclass);


--
-- Name: downtime_events event_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.downtime_events ALTER COLUMN event_id SET DEFAULT nextval('public.downtime_events_event_id_seq'::regclass);


--
-- Name: effectiveness_metrics metric_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.effectiveness_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.effectiveness_metrics_metric_id_seq'::regclass);


--
-- Name: equipment_metrics equipment_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.equipment_metrics ALTER COLUMN equipment_id SET DEFAULT nextval('public.equipment_metrics_equipment_id_seq'::regclass);


--
-- Name: equipment_reliability reliability_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.equipment_reliability ALTER COLUMN reliability_id SET DEFAULT nextval('public.equipment_reliability_reliability_id_seq'::regclass);


--
-- Name: failure_events failure_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.failure_events ALTER COLUMN failure_id SET DEFAULT nextval('public.failure_events_failure_id_seq'::regclass);


--
-- Name: financial_impact impact_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.financial_impact ALTER COLUMN impact_id SET DEFAULT nextval('public.financial_impact_impact_id_seq'::regclass);


--
-- Name: industry_benchmarks benchmark_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.industry_benchmarks ALTER COLUMN benchmark_id SET DEFAULT nextval('public.industry_benchmarks_benchmark_id_seq'::regclass);


--
-- Name: maintenance_targets target_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.maintenance_targets ALTER COLUMN target_id SET DEFAULT nextval('public.maintenance_targets_target_id_seq'::regclass);


--
-- Name: manufacturing_acronyms acronym_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturing_acronyms ALTER COLUMN acronym_id SET DEFAULT nextval('public.manufacturing_acronyms_acronym_id_seq'::regclass);


--
-- Name: non_conformant_materials ncm_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.non_conformant_materials ALTER COLUMN ncm_id SET DEFAULT nextval('public.non_conformant_materials_ncm_id_seq'::regclass);


--
-- Name: product_defects defect_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_defects ALTER COLUMN defect_id SET DEFAULT nextval('public.product_defects_defect_id_seq'::regclass);


--
-- Name: product_lines product_line_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_lines ALTER COLUMN product_line_id SET DEFAULT nextval('public.product_lines_product_line_id_seq'::regclass);


--
-- Name: production_lines line_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_lines ALTER COLUMN line_id SET DEFAULT nextval('public.production_lines_line_id_seq'::regclass);


--
-- Name: production_quality quality_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_quality ALTER COLUMN quality_id SET DEFAULT nextval('public.production_quality_quality_id_seq'::regclass);


--
-- Name: production_schedule schedule_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_schedule ALTER COLUMN schedule_id SET DEFAULT nextval('public.production_schedule_schedule_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: quality_costs cost_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.quality_costs ALTER COLUMN cost_id SET DEFAULT nextval('public.quality_costs_cost_id_seq'::regclass);


--
-- Name: quality_incidents incident_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.quality_incidents ALTER COLUMN incident_id SET DEFAULT nextval('public.quality_incidents_incident_id_seq'::regclass);


--
-- Name: schema_edges edge_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.schema_edges ALTER COLUMN edge_id SET DEFAULT nextval('public.schema_edges_edge_id_seq'::regclass);


--
-- Name: suppliers supplier_id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.suppliers ALTER COLUMN supplier_id SET DEFAULT nextval('public.suppliers_supplier_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: corrective_actions corrective_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.corrective_actions
    ADD CONSTRAINT corrective_actions_pkey PRIMARY KEY (capa_id);


--
-- Name: daily_deliveries daily_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.daily_deliveries
    ADD CONSTRAINT daily_deliveries_pkey PRIMARY KEY (delivery_id);


--
-- Name: downtime_events downtime_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.downtime_events
    ADD CONSTRAINT downtime_events_pkey PRIMARY KEY (event_id);


--
-- Name: effectiveness_metrics effectiveness_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.effectiveness_metrics
    ADD CONSTRAINT effectiveness_metrics_pkey PRIMARY KEY (metric_id);


--
-- Name: equipment_metrics equipment_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.equipment_metrics
    ADD CONSTRAINT equipment_metrics_pkey PRIMARY KEY (equipment_id);


--
-- Name: equipment_reliability equipment_reliability_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.equipment_reliability
    ADD CONSTRAINT equipment_reliability_pkey PRIMARY KEY (reliability_id);


--
-- Name: failure_events failure_events_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.failure_events
    ADD CONSTRAINT failure_events_pkey PRIMARY KEY (failure_id);


--
-- Name: financial_impact financial_impact_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.financial_impact
    ADD CONSTRAINT financial_impact_pkey PRIMARY KEY (impact_id);


--
-- Name: industry_benchmarks industry_benchmarks_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.industry_benchmarks
    ADD CONSTRAINT industry_benchmarks_pkey PRIMARY KEY (benchmark_id);


--
-- Name: maintenance_targets maintenance_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.maintenance_targets
    ADD CONSTRAINT maintenance_targets_pkey PRIMARY KEY (target_id);


--
-- Name: manufacturing_acronyms manufacturing_acronyms_acronym_table_name_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturing_acronyms
    ADD CONSTRAINT manufacturing_acronyms_acronym_table_name_key UNIQUE (acronym, table_name);


--
-- Name: manufacturing_acronyms manufacturing_acronyms_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturing_acronyms
    ADD CONSTRAINT manufacturing_acronyms_pkey PRIMARY KEY (acronym_id);


--
-- Name: non_conformant_materials non_conformant_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.non_conformant_materials
    ADD CONSTRAINT non_conformant_materials_pkey PRIMARY KEY (ncm_id);


--
-- Name: product_defects product_defects_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_defects
    ADD CONSTRAINT product_defects_pkey PRIMARY KEY (defect_id);


--
-- Name: product_lines product_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.product_lines
    ADD CONSTRAINT product_lines_pkey PRIMARY KEY (product_line_id);


--
-- Name: production_lines production_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_lines
    ADD CONSTRAINT production_lines_pkey PRIMARY KEY (line_id);


--
-- Name: production_quality production_quality_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_quality
    ADD CONSTRAINT production_quality_pkey PRIMARY KEY (quality_id);


--
-- Name: production_schedule production_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.production_schedule
    ADD CONSTRAINT production_schedule_pkey PRIMARY KEY (schedule_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: quality_costs quality_costs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.quality_costs
    ADD CONSTRAINT quality_costs_pkey PRIMARY KEY (cost_id);


--
-- Name: quality_incidents quality_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.quality_incidents
    ADD CONSTRAINT quality_incidents_pkey PRIMARY KEY (incident_id);


--
-- Name: schema_edges schema_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.schema_edges
    ADD CONSTRAINT schema_edges_pkey PRIMARY KEY (edge_id);


--
-- Name: schema_nodes schema_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.schema_nodes
    ADD CONSTRAINT schema_nodes_pkey PRIMARY KEY (table_name);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (supplier_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_acronym; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_acronym ON public.manufacturing_acronyms USING btree (acronym);


--
-- Name: idx_table_name; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX idx_table_name ON public.manufacturing_acronyms USING btree (table_name);


--
-- Name: corrective_actions corrective_actions_ncm_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.corrective_actions
    ADD CONSTRAINT corrective_actions_ncm_id_fkey FOREIGN KEY (ncm_id) REFERENCES public.non_conformant_materials(ncm_id);


--
-- Name: daily_deliveries daily_deliveries_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.daily_deliveries
    ADD CONSTRAINT daily_deliveries_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(supplier_id);


--
-- Name: downtime_events downtime_events_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.downtime_events
    ADD CONSTRAINT downtime_events_line_id_fkey FOREIGN KEY (line_id) REFERENCES public.production_lines(line_id);


--
-- Name: equipment_reliability equipment_reliability_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.equipment_reliability
    ADD CONSTRAINT equipment_reliability_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipment_metrics(equipment_id);


--
-- Name: manufacturing_acronyms manufacturing_acronyms_table_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.manufacturing_acronyms
    ADD CONSTRAINT manufacturing_acronyms_table_name_fkey FOREIGN KEY (table_name) REFERENCES public.schema_nodes(table_name);


--
-- Name: non_conformant_materials non_conformant_materials_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.non_conformant_materials
    ADD CONSTRAINT non_conformant_materials_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(supplier_id);


--
-- Name: quality_costs quality_costs_product_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.quality_costs
    ADD CONSTRAINT quality_costs_product_line_id_fkey FOREIGN KEY (product_line_id) REFERENCES public.product_lines(product_line_id);


--
-- Name: schema_edges schema_edges_from_table_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.schema_edges
    ADD CONSTRAINT schema_edges_from_table_fkey FOREIGN KEY (from_table) REFERENCES public.schema_nodes(table_name);


--
-- Name: schema_edges schema_edges_to_table_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.schema_edges
    ADD CONSTRAINT schema_edges_to_table_fkey FOREIGN KEY (to_table) REFERENCES public.schema_nodes(table_name);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

\unrestrict uzPEdw0gykufkLv7yMcJF3t2kTKlaIvTv8iXUwtHIPAVGbI6sDWDGRaOobUg7i7

