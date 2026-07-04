**Manufacturing and Manufacturing Resource Planning Terminology Used in Semantic Models**

*Ontologies, Taxonomies, Knowledge Graphs, and Semantic Layers for the Modern Factory*

*The convergence of industrial operations, enterprise resource planning, and semantic knowledge modeling is redefining how manufacturers govern, share, and reason over production data.*

**Prepared for:** Manufacturing Data Architects, ERP/MES System Designers, Knowledge Engineers, OT Analysts, and Enterprise Information Managers

**Prepared by:** William  |  Kent, Washington, United States

**Date:** June 18, 2026  |  Pacific Daylight Time

**Classification:** Internal Reference  |  Version 1.0

# Table of Contents

**Executive Summary**

**Section 1 — Introduction**

**Section 2 — The Manufacturing Domain: A Terminology Overview**

2.1 The Manufacturing Enterprise Stack

2.2 Core Manufacturing Process Terms

2.3 Inventory and Material Terms

**Section 3 — Manufacturing Resource Planning (MRP / MRP II) Terminology**

3.1 Origins and Evolution

3.2 Core MRP Terminology

3.3 Capacity Planning Terms

**Section 4 — Product and Process Ontologies in Manufacturing**

4.1 What Is a Manufacturing Ontology?

4.2 Major Manufacturing Ontologies and Standards

4.3 The Bill of Materials as a Semantic Graph

**Section 5 — Taxonomies in Manufacturing**

5.1 Product Taxonomies

5.2 Process and Operation Taxonomies

5.3 Geographic and Organizational Taxonomies

5.4 SKOS Representation of Manufacturing Taxonomies

**Section 6 — Knowledge Graphs in Manufacturing**

6.1 The Manufacturing Knowledge Graph

6.2 Manufacturing Knowledge Graph Applications

6.3 Comparison: Knowledge Graph vs. Traditional Manufacturing Data Systems

6.4 Real-World Manufacturing Knowledge Graph Examples

**Section 7 — Semantic Layers in Manufacturing ERP and MES**

7.1 The Semantic Layer in Manufacturing Analytics

7.2 Key Manufacturing Semantic Layer Metrics and Dimensions

7.3 ISA-95 as the Semantic Layer Foundation for MES

**Section 8 — Semantic Modeling Patterns for Manufacturing**

8.1–8.6 Six Canonical Patterns  |  8.7 Governance and Stewardship

**Section 9 — Digital Twins and Industry 4.0 Semantic Terminology**

**Section 10 — Tool Landscape for Manufacturing Semantic Models**

**Section 11 — Reference Architecture: Manufacturing Semantic Model**

**Section 12 — Conclusion and Recommendations**

**Glossary**

# Executive Summary

Modern manufacturing enterprises operate across a labyrinth of software systems — Enterprise Resource Planning (ERP), Manufacturing Execution Systems (MES), Supervisory Control and Data Acquisition (SCADA), Product Lifecycle Management (PLM), and Industrial Internet of Things (IIoT) platforms — each maintaining its own terminology, data models, and representational conventions. A production order in SAP S/4HANA, a work order in Rockwell FactoryTalk, a manufacturing order in Oracle Cloud Manufacturing, and a job in a shop-floor scheduling tool may all refer to the same industrial object; yet from a data integration perspective, they are invisible to one another. This **terminological fragmentation** is not a minor inconvenience — it is a structural liability that causes integration failures, corrupts analytics, impedes compliance reporting, and prevents the realization of digital transformation investments.

Semantic models — encompassing ontologies, taxonomies, knowledge graphs, and semantic layers — provide the unifying framework to resolve this fragmentation. By expressing manufacturing concepts in machine-interpretable, formally defined structures (OWL, RDF, SKOS), organizations can achieve **semantic interoperability**: the ability for disparate systems to share not merely data, but shared meaning. Where traditional data integration moves bytes between tables, semantic integration moves understood concepts between reasoning engines.

The imperative is sharpened by the demands of **Industry 4.0**, digital twins, and AI-driven manufacturing operations. Digital twins require a semantic backbone to link virtual representations to their physical counterparts. AI systems — whether machine learning models predicting equipment failure or large language models grounding operational queries — require structured, factual knowledge bases to reason reliably about production environments. Semantic models built on manufacturing-specific ontologies and taxonomies provide precisely this infrastructure.

This document delivers a **structured reference of manufacturing and MRP terminology as applied in semantic models**. It is organized to serve both the terminological education of practitioners new to semantic manufacturing and the practical pattern library needs of architects designing semantic integration systems. Sections progress from foundational manufacturing vocabulary through MRP and ERP terminology, into formal ontology and taxonomy standards, knowledge graph architectures, and concluding with actionable implementation patterns and a comprehensive glossary of over forty defined terms.

# Section 1 — Introduction

Walk onto any large manufacturing shop floor and you will find a paradox: extraordinary physical precision — tolerances measured in microns, production schedules governed by minute-level takt times — coexisting with remarkable terminological disorder. The concept of a "work order" alone is named differently in virtually every system a manufacturer runs: **Production Order** in SAP, **Work Order** in Oracle Manufacturing Cloud, **Job Order** in Epicor, **Manufacturing Batch** in process industry MES platforms, and simply a "traveler" on the physical shop floor. Each system encodes the concept in different database schemas, with different field names, different status codes, and different lifecycle semantics. The manufacturing enterprise has achieved operational excellence in the physical domain while remaining semantically chaotic in the information domain.

This fragmentation is not merely aesthetic. It creates measurable integration friction: ETL pipelines that break when field names change, analytics reports that double-count or miss production quantities because "completed" means different things to the MES and the ERP, and compliance reporting failures because a regulatory query crosses system boundaries without a common vocabulary to traverse. As manufacturing organizations scale — through acquisitions, geographic expansion, or supply chain deepening — the semantic chaos compounds geometrically.

The **semantic modeling imperative** emerges from this context. Where previous generations of integration relied on syntactic data exchange (agreeing on file formats, XML schemas, or API contracts), semantic interoperability requires agreement on meaning: that a concept called "ProductionOrder" in one system and "WorkOrder" in another refers to the same real-world object, with the same properties, lifecycle states, and relationships to materials and operations. Achieving this requires formal, machine-interpretable representations — the domain of semantic web technologies.

The foundational technologies are now mature and increasingly adopted in industrial contexts. **RDF (Resource Description Framework)** provides a universal data model for expressing facts as subject–predicate–object triples. **OWL (Web Ontology Language)** enables the expression of formal class hierarchies, property definitions, and logical constraints — the building blocks of manufacturing ontologies. **SKOS (Simple Knowledge Organization System)** provides a lightweight vocabulary for taxonomies and controlled vocabularies, ideal for encoding product classifications, operation type hierarchies, and defect taxonomies. **SPARQL** provides a query language over RDF knowledge graphs, enabling complex traversals across product, process, equipment, and quality data that would require dozens of SQL joins across siloed relational systems.

Applied to manufacturing, these technologies are no longer experimental. Standards bodies including ISA (International Society of Automation), IEC (International Electrotechnical Commission), and W3C have produced formal models: ISA-95/IEC 62264 defines the canonical object model for manufacturing operations management; ISO 15926 governs lifecycle data integration for process plants; SAREF4INMA extends IoT semantic standards into the industrial manufacturing domain. Commercial platforms including Siemens, SAP, and Microsoft are embedding knowledge graph capabilities into their core manufacturing product portfolios.

## Historical Context

The history of manufacturing data modeling parallels the history of manufacturing itself. **Bill of Materials** data existed first as paper cards and engineering drawings. The 1960s and 1970s saw the mechanization of BOM management and the development, by Joseph Orlicky at IBM, of **Material Requirements Planning (MRP)** — a computational engine that for the first time enabled systematic time-phased calculation of component requirements from a production schedule. Oliver Wight extended MRP in the 1980s to **MRP II (Manufacturing Resource Planning)**, integrating capacity planning, financial simulation, and shop-floor control. The 1990s saw the emergence of integrated **ERP systems** — SAP R/3 (1992), Oracle Manufacturing, Baan — that unified MRP II with finance, HR, and procurement into a single relational database architecture.

By the 2010s, the limitations of relational ERP architectures for cross-system semantic integration became apparent, spurring academic and industrial research into manufacturing ontologies: **MASON** (Manufacturing's Semantics Ontology), **PURO** (Process Understanding and Representation Ontology), and the application of ISO 15926 to process industry data. By the 2020s, digital twin platforms and AI-driven manufacturing applications were demanding semantic backbones that ERP databases alone could not provide. This document addresses that demand.

Each subsequent section of this document builds systematically toward a complete reference model: Section 2 establishes the manufacturing terminology foundation; Section 3 covers MRP/MRP II vocabulary; Sections 4–5 address formal ontologies and taxonomies; Sections 6–7 examine knowledge graphs and semantic layers; Section 8 delivers practical implementation patterns; and Sections 9–12 address Industry 4.0 terminology, tool landscapes, reference architecture, and recommendations.

# Section 2 — The Manufacturing Domain: A Terminology Overview

## 2.1 The Manufacturing Enterprise Stack

Manufacturing enterprises are organized as a layered stack of operational systems, each serving distinct functions, each generating distinct data, and each — critically — developing its own terminology conventions. Understanding this stack is prerequisite to understanding why semantic integration is structurally necessary, not optional.

| Level | Systems | Primary Function | Terminology Domain |
| --- | --- | --- | --- |
| Level 0–1: Field Devices | PLCs, sensors, actuators, drives | Physical process control; measurement and actuation | Tag names, register addresses, engineering units (°C, bar, RPM) |
| Level 2: SCADA / DCS | OSIsoft PI, AVEVA, Ignition SCADA, Honeywell DCS | Supervisory monitoring, historian data collection, alarming | Process variable names, alarm codes, batch IDs, tag hierarchies |
| Level 3: MES / MOM | Siemens OPCENTER, Rockwell FactoryTalk, Apriso, AVEVA MES | Production execution, dispatching, genealogy, quality | Work orders, operations, work centers, materials, lots, genealogy |
| Level 4: ERP | SAP S/4HANA, Oracle Cloud Manufacturing, Microsoft Dynamics 365 | Planning, procurement, finance, inventory, sales | Production orders, BOMs, routings, material masters, cost centers |
| Level 5: Enterprise Analytics / Cloud | Azure IoT, AWS IoT, SAP BTP, Power BI, digital twin platforms | Analytics, AI/ML, digital twin, business intelligence | KPIs (OEE, OTD, FPY), asset models, event streams, dashboards |

Each level of this stack generates data that is meaningful only within that level's own vocabulary. A **PLC (Programmable Logic Controller)** at Level 0–1 knows nothing of production orders; it knows tag addresses and register values. The SCADA historian at Level 2 knows process variables and timestamps but does not understand BOM relationships. The MES at Level 3 knows work orders and operations but may not know the financial cost center to which production costs must be allocated. The ERP at Level 4 knows the production order and cost center but typically has only summary access to machine-level sensor data. The enterprise analytics layer at Level 5 needs all of this integrated — and semantic models are the integration mechanism.

## 2.2 Core Manufacturing Process Terms

**Manufacturing** is the transformation of raw materials, components, or semi-finished goods into finished products through physical, chemical, or assembly processes. In semantic models, Manufacturing is typically represented as an OWL superclass with subclasses for discrete manufacturing (individual unit production), process manufacturing (batch or continuous flow), and additive manufacturing (layer-by-layer fabrication).

**Production Planning** is the process of determining what to manufacture, in what quantities, and on what schedule, balancing demand forecasts against capacity constraints and inventory levels. It is the bridge between market demand signals (customer orders, forecasts) and shop-floor execution instructions (production orders, work center schedules).

**Shop Floor** refers to the physical area where manufacturing operations are executed — where machines, operators, tooling, and materials converge to produce goods. In ISA-95 ontology terms, the shop floor corresponds to the Work Center and Work Unit levels of the equipment hierarchy. It is the primary domain of MES systems and the source of real-time operational event data.

**Work Center** is a defined grouping of machines, tools, or labor resources used to perform specific manufacturing operations. Work centers are the fundamental unit of capacity planning: available capacity is expressed as hours available per work center per planning period. In OWL ontologies, WorkCenter is a class with properties for capacity, shift calendar, efficiency rating, and location within the ISA-95 hierarchy.

**Routing** is the defined sequence of operations, work centers, and time standards required to manufacture one unit of a product. A routing is the process analogue of a Bill of Materials: where the BOM defines the material structure of a product, the routing defines its process structure. In semantic models, a routing is represented as an ordered sequence of Operation individuals, linked by hasNextOperation ObjectProperties.

**Operation** is a single step within a manufacturing routing. Each operation specifies the work center where it is performed, the standard setup time (time to prepare the work center), the standard run time per unit produced, and any tooling or resource requirements. Operations are the granular building blocks of production scheduling and cost accumulation.

**Production Order (Work Order)** is a formal shop-floor document — in paper or electronic form — that authorizes the manufacture of a specified quantity of a product by a target completion date. It links together the material (what is being made), the BOM (what materials are needed), the routing (how it is made), the quantities, and the time schedule. In semantic models, ProductionOrder is a central hub class connected by ObjectProperties to Product, BOM, Routing, WorkCenter, Personnel, QualityInspection, and MaterialMovement individuals.

**Capacity Planning** is the process of determining the production capacity needed to meet demand, expressed in machine hours or labor hours per work center per planning period. It compares required capacity (derived from planned production orders and routing time standards) against available capacity (derived from shift calendars and work center ratings) to identify over- or under-load conditions.

**Throughput** is the rate at which a manufacturing system produces finished goods, typically expressed in units per hour or units per shift. It is a primary operational performance metric and a key concept in Theory of Constraints (TOC) manufacturing philosophy, where the goal is to maximize throughput while reducing inventory and operating expense.

## 2.3 Inventory and Material Terms

**Stock Keeping Unit (SKU)** is the lowest-level unique identifier for a product variant — the atomic unit of inventory management. Every distinct product configuration, color, size, or packaging type receives its own SKU. In semantic models, SKU is typically a DatatypeProperty of the Product class, linked to a specific instance of a product variant individual.

**Raw Material** is unprocessed input material consumed in manufacturing operations but not itself a manufactured product. Raw materials sit at the deepest levels of the Bill of Materials hierarchy (Level N) and are typically sourced from external suppliers rather than produced internally.

**Work in Process (WIP)** refers to partially manufactured goods currently in production — units for which manufacturing has begun but not yet completed. WIP represents accumulated material and labor value. Tracking WIP in semantic models requires linking ProductionOrder individuals to OperationCompletion events, accumulating cost and quantity at each operation step.

**Finished Goods** are completed products that have passed quality inspection and are ready for sale or distribution. In the BOM hierarchy, finished goods occupy Level 0 — the top of the product structure. Their inventory value includes all accumulated material, labor, and overhead costs from the manufacturing routing.

**Safety Stock** is buffer inventory maintained above the expected demand level to guard against demand uncertainty or supply variability. It is a quantity expressed in units and is a property of the Material–Location combination in ERP systems. In semantic models, safetyStockQuantity is a DatatypeProperty of the MaterialLocation class.

**Reorder Point** is the inventory level at which a replenishment order must be triggered to avoid stockout before the next replenishment arrives. It is calculated as: average demand during lead time plus safety stock. In MRP-managed items, the reorder point concept is superseded by time-phased net requirements calculations, but it remains relevant for min-max inventory management of C-class items.

# Section 3 — Manufacturing Resource Planning (MRP / MRP II) Terminology

## 3.1 Origins and Evolution

**Material Requirements Planning (MRP)** was developed in the 1960s and 1970s by Joseph Orlicky at IBM, building on earlier work by George Plossl and Oliver Wight. It is, at its core, a deterministic calculation engine: given a Master Production Schedule (what finished goods to produce and when), a set of Bills of Materials (what components are needed), and current inventory levels, MRP calculates the time-phased quantities of each component that must be either manufactured or purchased to support the production plan. MRP transformed manufacturing planning from intuition-based ordering to systematic, computer-driven calculation of dependent demand.

**MRP II (Manufacturing Resource Planning)** extended MRP beyond material requirements into the broader domain of manufacturing resource management. Coined and developed by Oliver Wight in the 1980s, MRP II added capacity requirements planning (to validate that the production plan is feasible given work center capacities), shop-floor control (to manage the execution of production orders), demand management (to coordinate customer orders and forecasts), and financial simulation (to project the cost of the production plan). MRP II was a closed-loop planning system: execution data fed back into planning, enabling continuous replanning as reality diverged from plan.

The evolution to **ERP (Enterprise Resource Planning)** in the 1990s — most notably with the launch of SAP R/3 in 1992 — integrated MRP II with financial accounting, human resources, procurement, and sales into a single unified database architecture. ERP systems became the dominant paradigm for manufacturing management, encoding MRP II logic as core computational modules (Production Planning in SAP PP, Oracle Manufacturing) while adding enterprise-wide integration capabilities that MRP II standalone systems lacked.

## 3.2 Core MRP Terminology

The following terms constitute the canonical vocabulary of MRP/MRP II as used in both ERP implementations and semantic manufacturing models. Each term is defined with its semantic modeling relevance noted where applicable.

**Master Production Schedule (MPS)** is the time-phased plan that states which end items (Level 0 BOM items — finished goods or major subassemblies) will be produced, in what quantities, and in which time periods. The MPS is the primary driver of the entire MRP calculation chain. It represents the manufacturing enterprise's production commitment, balancing customer demand against capacity constraints and inventory targets.

| ◆ Semantic Modeling Note — Master Production Schedule In manufacturing ontologies, MasterProductionSchedule is an OWL class whose instances link to Product individuals (what is being scheduled), TimePeriod individuals (the planning bucket), and QuantityValue individuals (the planned production quantity). The MPS class sits at the apex of the planning hierarchy, with ObjectProperties connecting downward to PlannedOrder and ProductionOrder individuals generated by MRP explosion. Temporal properties (scheduleStart, scheduleEnd, bucketType) are DatatypeProperties on the MPS individual. |
| --- |

**Bill of Materials (BOM)** is a hierarchical, structured list of all components, sub-assemblies, and raw materials required to manufacture one unit of a parent item, together with the quantities required per parent unit and the units of measure. The BOM is arguably the single most important data structure in discrete manufacturing — it is the foundation of MRP calculations, product costing, procurement planning, and quality traceability. A BOM may exist in multiple engineering variants (Engineering BOM or EBOM) and manufacturing-specific variants (Manufacturing BOM or MBOM), which may differ as the design is adapted for production efficiency.

**BOM Level** designates the position of a component within the BOM hierarchy. Level 0 is the finished product (the item being manufactured). Level 1 components are direct sub-assemblies or materials consumed directly in the final assembly operation. Deeper levels represent the sub-assemblies and components of those Level 1 items, recursing until raw materials are reached. BOM explosion — the recursive expansion of a BOM from Level 0 through all levels — is the central computational act of MRP.

**Net Requirements** represent the uncovered demand for a component after accounting for on-hand inventory and scheduled receipts (open purchase orders and production orders). MRP calculates net requirements for each component in each time bucket: Net Requirements = Gross Requirements − On-Hand Inventory − Scheduled Receipts. Net requirements drive planned order generation.

**Gross Requirements** represent the total demand for a component from all parent item production orders across all time buckets in the planning horizon. They are computed by multiplying planned quantities of each parent item by the BOM quantity of the component. Gross requirements represent demand before offsetting with available supply.

**Planned Order** is a system-generated recommendation — produced by the MRP engine — to manufacture or purchase a quantity of a component to satisfy net requirements. Planned orders are not yet released to the shop floor or to suppliers; they represent the MRP system's suggested action. They can be automatically converted to production orders or purchase orders, or reviewed and modified by planners before release.

**Firm Planned Order (FPO)** is a planned order that has been manually reviewed and confirmed by a planner. Unlike a standard planned order, an FPO is protected from automatic rescheduling by the MRP engine — it will not be moved, split, or cancelled in the next MRP run without planner intervention. FPOs are used when planners need to override MRP's automatic logic to accommodate real-world constraints.

**Time Bucket** is the planning period unit over which MRP aggregates requirements and calculates planned orders. Common time buckets are one day (daily buckets) or one week (weekly buckets). The choice of time bucket affects planning precision: daily buckets provide finer control but generate larger data volumes; weekly buckets are computationally lighter but may obscure within-week demand patterns.

**Lead Time** is the total elapsed time from when an order is placed to when the ordered goods are available for use. For manufactured items, lead time is composed of: queue time (time waiting before an operation begins), setup time (time to prepare the work center), run time (time to complete the production quantity), move time (time to transport between operations), and wait time (time after an operation before the next begins). For purchased items, lead time is the vendor's delivery time. Lead time is used by MRP to offset planned order release dates from their required dates.

**Lot Sizing** is the rule that determines the quantity of a planned order. MRP does not inherently dictate lot sizes — various policies may be applied. Common lot-sizing methods include:

- **Lot-for-Lot (LFL):** Order exactly the net requirement quantity in each period; minimizes inventory but may maximize order frequency and setup costs.
- **Economic Order Quantity (EOQ):** Orders a fixed quantity calculated to minimize the sum of ordering costs and inventory carrying costs.
- **Fixed Order Quantity (FOQ):** Always orders a fixed predetermined quantity, regardless of net requirements.
- **Period Order Quantity (POQ):** Combines net requirements across multiple periods into a single order, reducing ordering frequency.
- **Minimum Order Quantity (MOQ):** Enforces a supplier-defined minimum purchase quantity.

**Safety Lead Time** is an artificial buffer added to the calculated lead time to protect against supply uncertainty and variability in production or delivery times. It is a time-based buffer (measured in days), as distinct from safety stock, which is a quantity-based buffer. Both may be applied simultaneously for critical components.

**Pegging** is the ability to trace a component requirement back through the BOM hierarchy to the original demand source — typically a customer order or forecast. Pegging enables planners to understand the impact of supply problems: if a critical component is short, pegging identifies which customer orders are at risk. In semantic models, pegging is a natural capability of graph traversal: a SPARQL query traverses the hasPart and dependsOnOrder ObjectProperties upward through the BOM graph to the originating SalesOrder individual.

## 3.3 Capacity Planning Terms

**Rough-Cut Capacity Planning (RCCP)** is a high-level, pre-MRP check of whether the Master Production Schedule is feasible against key resource capacities — the production lines, machines, or labor pools that are most likely to constrain output. RCCP uses simplified resource profiles (units of capacity consumed per MPS item) rather than detailed routings, enabling fast feasibility assessment before the computationally intensive full MRP explosion is executed.

**Capacity Requirements Planning (CRP)** is the detailed calculation of the capacity required at each work center in each time period, derived from MRP planned orders and their associated routings. CRP computes the load profile for each work center: the total machine-hours or labor-hours required, operation by operation, across all open and planned production orders. CRP output is compared against available capacity to identify bottlenecks.

| ⚠ Key Distinction: RCCP vs. CRP RCCP operates at the MPS level — it checks whether the overall production plan is feasible before MRP runs. CRP operates at the MRP output level — it validates detailed work center loads after MRP has generated planned orders. RCCP is fast and approximate; CRP is slow and precise. In semantic models, both are expressed as capacity constraint classes with ObjectProperties linking to WorkCenter, TimePeriod, and ProductionPlan individuals — but with different levels of granularity in routing resolution. |
| --- |

**Available Capacity** is the total productive capacity a work center can deliver in a planning period, accounting for scheduled downtime, planned maintenance, shift patterns, and efficiency ratings. It is the supply side of the capacity equation. Available capacity is typically defined in the work center master data of the ERP system, drawing on factory calendars and shift definitions.

**Demonstrated Capacity** is the actual historical capacity delivered by a work center over a representative past period — what the work center has actually produced, as distinguished from its theoretical or rated capacity. Demonstrated capacity accounts for real-world inefficiencies: unexpected downtime, quality rework, operator performance variation, and material shortages. It is the most reliable input for realistic capacity planning parameters.

**Load Profile** is a time-phased summary of the planned capacity load at a work center — the total hours of planned production work per time bucket. A load profile visualizes over-load (load exceeds available capacity) and under-load (load is below available capacity) across the planning horizon. It is the primary output of CRP and the primary input to production scheduling decisions.

# Section 4 — Product and Process Ontologies in Manufacturing

## 4.1 What Is a Manufacturing Ontology?

A **manufacturing ontology** is a formal, machine-interpretable model of manufacturing concepts, their defining properties, and the relationships between them, expressed in OWL/RDF or equivalent semantic formalisms. Unlike a data dictionary (which defines terms for human readers) or a database schema (which defines data structures for a specific application), an ontology defines concepts with sufficient precision and logical constraint to support automated reasoning — the ability for a machine to infer new facts from stated facts and defined rules.

The motivation for manufacturing ontologies is direct: heterogeneous systems (SAP, Oracle, AVEVA, Rockwell), heterogeneous standards (ISO, IEC, ANSI, ASTM, GS1), and heterogeneous data formats (XML, JSON, relational databases, time series historians) all use different names, different structures, and different semantic conventions to describe the same industrial reality. A manufacturing ontology provides the shared conceptual reference model against which all of these system-specific representations can be mapped, enabling a form of integration that goes beyond data format conversion to achieve genuine semantic alignment.

The role of ontologies in manufacturing extends across several integration scenarios: connecting ERP material master data to MES work order execution data; linking PLM product structures to manufacturing process plans; associating equipment sensor streams with maintenance work orders; and grounding AI queries about production status in factual, structured knowledge bases.

## 4.2 Major Manufacturing Ontologies and Standards

The following ontologies and standards constitute the primary reference landscape for manufacturing semantic modeling practitioners.

**MASON (Manufacturing's Semantics Ontology)** was one of the earliest OWL-based manufacturing ontologies, developed in the mid-2000s to formally model manufacturing processes, resources, and products. MASON established a class hierarchy for manufacturing processes (with subclasses for forming, material removal, assembly, and joining), manufacturing resources (machines, tools, labor), and manufactured products. While MASON itself has been superseded by more comprehensive standards, it established foundational patterns that influenced subsequent ontology development.

**PURO (Process Understanding and Representation Ontology)** is an upper-level manufacturing process ontology covering manufacturing processes, resources, and capabilities. PURO focuses on the relationship between manufacturing capabilities (what a resource can do) and process requirements (what a process needs), enabling automated capability matching — determining which machines or work centers can execute which operations. This capability matching function is directly applicable to digital manufacturing planning and scheduling systems.

**ISO 15926** is the international standard for lifecycle integration of process plant data, widely used in oil, gas, chemical, and offshore manufacturing. ISO 15926 Part 2 defines a top-level data model compatible with RDF, and the Reference Data Library (RDL) provides a large catalog of formally defined concepts for process equipment, materials, and activities. ISO 15926 is particularly mature in the engineering and construction phase of plant lifecycle management.

**IEC 61360 / Common Data Dictionary (CDD)** is the IEC standard for defining properties of technical objects — it provides a formal framework for specifying what properties a class of objects has, including data types, units of measure, and value ranges. The IEC CDD is the conceptual foundation for both the ECLASS product classification standard and the eCl@ss standard. Properties defined in IEC 61360 format are directly mappable to OWL datatype properties with formal domain and range constraints.

**SAREF4INMA** (Smart Appliances Reference ontology extension for Industry and Manufacturing) is an ETSI standard extending the SAREF IoT ontology into the manufacturing domain. SAREF4INMA defines concepts for production batches, features of interest, and measurements as applied in industrial manufacturing contexts. It provides the semantic bridge between IIoT sensor observations and manufacturing process events, enabling OEE calculations and quality analytics that span both the sensor data and the production order domains.

**ISA-95 / IEC 62264** is the most operationally significant standard for manufacturing semantic modeling. Published jointly by the International Society of Automation (ISA) and IEC, ISA-95 defines a hierarchical equipment model (Enterprise → Site → Area → Work Center → Work Unit) and a comprehensive set of manufacturing operations management (MOM) data models covering production scheduling, dispatching, execution, data collection, quality management, inventory management, and maintenance management. ISA-95 Part 2 object models are the de facto ontological reference for MES data integration and the primary source of class hierarchies for manufacturing knowledge graph construction.

| ◈ ISA-95 Equipment Hierarchy as OWL Class Structure The ISA-95 equipment hierarchy provides a ready-made OWL class hierarchy for physical manufacturing locations and resources: • Enterprise (top-level organizational entity — the legal company) • Site (a geographic manufacturing location — a plant or facility) • Area (a functional zone within a site — painting department, assembly hall) • Work Center (a group of work units performing related operations) • Work Unit (an individual machine, cell, or operator station) Each level is an OWL class. The isPartOf ObjectProperty links child to parent, creating a traversable hierarchy. Equipment properties (capacity, shift calendar, location coordinates, maintenance status) are DatatypeProperties on each individual. SPARQL queries can traverse this hierarchy to aggregate OEE metrics from Work Unit level up to Site or Enterprise level — a query that would require dozens of SQL joins in a conventional relational data warehouse. |
| --- |

**Schema.org Manufacturing Extensions** represent an emerging use of the Schema.org vocabulary — originally designed for web content annotation — for manufacturing entity description in public-facing linked data contexts. Schema.org *Product*, *Offer*, and *Organization* classes provide lightweight representations of finished goods, supplier relationships, and manufacturing entities suitable for supply chain interoperability and e-commerce integration scenarios where formal OWL reasoning is not required.

## 4.3 The Bill of Materials as a Semantic Graph

The Bill of Materials is structurally one of the most natural candidates for semantic graph representation in manufacturing. A multi-level BOM is, mathematically, a **directed acyclic graph (DAG)**: nodes are components (products, sub-assemblies, raw materials), and directed edges represent the "is a component of" relationship, with quantity annotations on each edge. This graph structure maps directly and naturally to OWL ObjectProperty assertions and RDF triples.

In a relational ERP database, a multi-level BOM is typically stored as a flat table of parent–child relationships (MAST and MPOS tables in SAP, for example), and BOM explosion requires iterative SQL queries or stored procedures to traverse the hierarchy. In a semantic graph, BOM explosion is a natural SPARQL recursive traversal — a single parameterized query that traverses the *hasPart* ObjectProperty from the root Product individual through all levels of the BOM to enumerate all component requirements.

| ◆ Semantic BOM Model: Key Pattern In a semantic BOM model, each component is an OWL individual of class ManufacturedItem or PurchasedItem. The hasPart ObjectProperty links parent to child, and the quantityPerParent DatatypeProperty records the usage quantity per parent unit. The unitOfMeasure ObjectProperty links to a QUDT unit individual. Effective dates (effectiveFrom, effectiveTo) are DatatypeProperties supporting time-bounded BOM versions. A multi-level BOM explosion is expressed as a SPARQL property path query using the hasPart+ transitive closure operator, replacing traditional recursive SQL or MRP explosion stored procedures. The query returns all component individuals at all BOM levels in a single traversal, naturally accumulating quantities through the hierarchy. Engineering Change Notices (ECNs) are modeled as ChangeEvent individuals linked to the BOM relationship via a modifiedBy ObjectProperty, enabling full version history of the BOM as a temporal graph — a capability that relational ERP BOM schemas support only awkwardly. |
| --- |

The properties on BOM relationships in a semantic model extend beyond simple quantity: unit of measure (aligned to QUDT or IEC 61360 unit classes), effective dates (enabling time-bounded BOM versions), phantom item flags (for intermediate assemblies that pass through without stock), and engineering change notice (ECN) linkage for BOM version management. Multi-level BOM explosion as a SPARQL graph traversal replaces traditional MRP explosion logic with a semantically richer, more maintainable, and more extensible computation.

# Section 5 — Taxonomies in Manufacturing

## 5.1 Product Taxonomies

Product taxonomies provide the hierarchical classification structures that organize manufactured products, components, raw materials, and services into meaningful categories for procurement, inventory management, analytics, and interoperability. Unlike ontologies (which define classes and their logical relationships), product taxonomies are primarily about hierarchical grouping and controlled vocabulary — the domain of SKOS rather than OWL.

**UNSPSC (United Nations Standard Products and Services Code)** is a four-level hierarchical taxonomy — Segment → Family → Class → Commodity — used internationally to classify products and services for procurement and spend analytics. Segment codes group broad categories (e.g., 31: Manufacturing Components and Supplies); Family codes narrow to product families (e.g., 3110: Structural components); Class codes define product types; Commodity codes identify specific product categories. UNSPSC is widely integrated into ERP purchasing modules and procurement analytics platforms, and its hierarchy is a natural candidate for SKOS ConceptScheme encoding.

**eCl@ss** is an ISO 13584- and IEC 61360-compliant product classification and description standard widely used in German and European manufacturing for product master data management, catalog exchange, and materials management. Unlike UNSPSC, which is primarily a classification hierarchy, eCl@ss also defines the properties (characteristics) that products in each class should have — providing both the taxonomy and the property schema. eCl@ss supports SKOS and OWL serialization, making it a particularly powerful foundation for manufacturing product ontologies that need both classification hierarchy and property definitions.

**GS1 Global Product Classification (GPC)** is the product taxonomy standard used in consumer goods manufacturing and retail supply chains for global interoperability. GPC organizes products into a Segment → Family → Class → Brick hierarchy, with Brick Attributes (product properties) defined at the Brick level. GS1 GPC is the basis for GTIN (Global Trade Item Number) product identification and is embedded in supply chain systems across the consumer goods, food and beverage, and pharmaceutical sectors.

**Custom enterprise product taxonomies** are internally developed hierarchical classification systems tailored to a specific manufacturer's product portfolio, raw material types, spare parts inventory, and indirect materials. While lacking external interoperability, custom taxonomies align precisely with the enterprise's commercial and operational structure. Best practice is to maintain custom taxonomies as SKOS ConceptSchemes with mappings (skos:exactMatch, skos:closeMatch) to external standards such as eCl@ss or UNSPSC, preserving internal alignment while enabling external interoperability.

## 5.2 Process and Operation Taxonomies

Process and operation taxonomies classify manufacturing activities into hierarchical structures for routing design, capacity planning, cost classification, and cross-plant standardization.

**Operation type taxonomies** organize manufacturing operations into a hierarchy: primary process categories (Forming, Removing, Joining, Coating, Inspecting) → process subcategories (Machining, Casting, Welding, Assembly) → specific operation types (CNC Turning, MIG Welding, Press-Fit Assembly). This taxonomy is used in ERP routing design to assign standard times, cost rates, and work center type requirements to operations. In SKOS, each operation type is a Concept with skos:broader linking to its parent category and skos:prefLabel encoding the canonical name. ERP-system-specific synonyms (e.g., SAP activity types, Oracle operation codes) are encoded as skos:altLabel values.

**Work center type taxonomies** classify work centers by capability category: CNC Machining Center, Assembly Line, Paint Booth, Test Station, Welding Cell. These taxonomies support capacity planning (grouping work centers by type for rough-cut capacity analysis) and scheduling (matching operation type requirements to work center capabilities).

**Defect taxonomies** are structured hierarchies of non-conformance types used in quality management systems. A defect taxonomy for a metal fabrication manufacturer might organize as: Defect Type → Visual Defect / Dimensional Defect / Functional Defect → Surface Scratch / Weld Porosity / Out-of-Tolerance Dimension. These taxonomies align to Six Sigma FMEA (Failure Mode and Effects Analysis) defect categories and are used in root cause analysis, supplier quality reporting, and process improvement analytics.

## 5.3 Geographic and Organizational Taxonomies

**Plant and site taxonomies** organize physical manufacturing locations into a hierarchy aligned with the ISA-95 equipment model: Enterprise → Site → Area → Production Line → Work Unit. In the SAP organizational model, this maps to the Client → Plant → Storage Location hierarchy, while Oracle Manufacturing uses the Organization → Subinventory → Locator structure. Encoding the ISA-95 site hierarchy as a SKOS ConceptScheme creates a location taxonomy that is system-agnostic and can serve as a common reference for cross-system reporting.

**Organizational taxonomies** — cost centers, profit centers, plant codes, and company codes — represent the enterprise's financial and managerial organizational structure. These taxonomies are critical for cost allocation (charging manufacturing costs to the correct cost center) and management reporting (aggregating performance metrics up the organizational hierarchy). As SKOS ConceptSchemes, organizational taxonomies provide the controlled vocabulary for organizational dimensions in manufacturing analytics.

## 5.4 SKOS Representation of Manufacturing Taxonomies

SKOS (Simple Knowledge Organization System) is the W3C standard for encoding controlled vocabularies, taxonomies, and thesauri as RDF. Its core constructs map directly to manufacturing taxonomy requirements:

- **skos:ConceptScheme** — the containing structure for a taxonomy (e.g., the UNSPSC scheme, the Operation Type scheme)
- **skos:Concept** — an individual term or category node within the taxonomy
- **skos:prefLabel** — the canonical, preferred label for the concept in a given language
- **skos:altLabel** — alternative labels, synonyms, and system-specific names (e.g., "Work Order" as altLabel for "Production Order" as prefLabel)
- **skos:notation** — formal codes used to identify the concept (UNSPSC codes, eCl@ss codes, SAP activity type codes)
- **skos:broader / skos:narrower** — parent–child hierarchy relationships
- **skos:scopeNote** — explanatory notes distinguishing concepts that vary by system context
- **skos:exactMatch / skos:closeMatch** — alignment mappings to equivalent concepts in external taxonomies

Scope notes are particularly valuable for manufacturing taxonomy governance: a skos:scopeNote on the "Production Order" concept can document precisely how its meaning differs in SAP (a PP order with cost accumulation), Oracle (a discrete job with associated cost element), and Rockwell FactoryTalk (a work order linked to a routing and BOM), providing human-readable disambiguation while the formal SKOS concept serves as the semantic anchor for data integration mappings.

# Section 6 — Knowledge Graphs in Manufacturing

## 6.1 The Manufacturing Knowledge Graph

A **manufacturing knowledge graph** is an integrated, graph-structured knowledge base that connects products, processes, resources, orders, quality events, and supply chain entities through typed, semantically annotated relationships. It is the realization of manufacturing ontologies and taxonomies in an operational data environment: where ontologies define the schema (the classes and properties), the knowledge graph populates that schema with actual production instances — specific products, specific work orders, specific machines, specific quality events.

The manufacturing knowledge graph differs fundamentally from both a relational data warehouse and a traditional ERP database. Where a data warehouse denormalizes data into star or snowflake schemas optimized for aggregate query performance, and where an ERP database normalizes data into relational tables optimized for transactional consistency, a knowledge graph is optimized for **connected traversal** — following chains of typed relationships across entity boundaries without schema rigidity, enabling queries that cross the conceptual boundaries between production, quality, equipment, and supply chain domains.

Key entity types in a manufacturing knowledge graph include: Product, Component, Material, Process, Operation, WorkCenter, ProductionOrder, PlannedOrder, Supplier, Customer, Equipment, MaintenanceEvent, QualityInspection, DefectReport, DigitalTwin, SensorObservation, and EngineeringChangeNotice. Each entity type is an OWL class; each instance is an OWL individual populated from source systems; and the relationships between them are OWL ObjectProperties traversable by SPARQL queries.

## 6.2 Manufacturing Knowledge Graph Applications

**Root cause analysis** is one of the highest-value applications of manufacturing knowledge graphs. When a quality defect is detected — a batch of components failing dimensional inspection — a SPARQL query traverses the knowledge graph from the QualityInspection individual through links to the ProductionOrder, the Operation (which step produced the defect), the WorkCenter (which machine), the Equipment (which specific asset), the MaintenanceHistory (when was it last maintained), the MaterialBatch (which lot of raw material was in use), and the Operator (who was running the machine). This multi-domain traversal — crossing quality, production, maintenance, material, and personnel data — would require complex multi-system queries in a conventional architecture but is a natural single graph traversal in a knowledge graph.

**Predictive maintenance** leverages the knowledge graph as the integration backbone connecting equipment entities to sensor observation streams, maintenance work order history, and FMEA failure mode taxonomies. Machine learning models consume the graph-structured feature set — equipment type, age, maintenance history, current sensor deviations — to predict remaining useful life and trigger preventive work orders. The knowledge graph provides the semantic context that transforms raw sensor numbers into meaningful equipment health indicators.

**Supply chain visibility** is achieved by extending the manufacturing knowledge graph through supplier entity connections — linking internal product and component entities to external supplier site entities, purchase order histories, delivery lead time observations, and supply risk classifications. Multi-tier supply chain transparency (knowing not just the Tier-1 supplier of a component but the Tier-2 raw material supplier that supplies the Tier-1) is naturally represented as a graph traversal across the Supplier entity network.

**Digital twin backbone**: the manufacturing knowledge graph serves as the semantic integration layer between physics-based simulation models (the virtual representation of a machine or process) and real-world operational data streams. The knowledge graph defines what the digital twin represents (the Equipment individual and its properties), what data it consumes (linked SensorObservation individuals), and how its state relates to production outcomes (linked ProductionRun and QualityInspection individuals).

**AI and LLM grounding in manufacturing**: Large language models applied to manufacturing operations — for natural language queries about production status, machine health, inventory levels, or quality trends — require structured, factual grounding to prevent hallucination. The manufacturing knowledge graph provides this grounding through retrieval-augmented generation (RAG) architectures, where LLM queries are enriched with facts retrieved from the SPARQL-accessible knowledge graph before response generation. This pattern is emerging as a critical use case for manufacturing knowledge graphs in 2025–2026.

## 6.3 Comparison: Knowledge Graph vs. Traditional Manufacturing Data Systems

| Dimension | Manufacturing Knowledge Graph | Relational ERP Database | MES Flat Data Store |
| --- | --- | --- | --- |
| Schema Flexibility | Open-world: new entity types and properties added without schema migration | Closed-world: schema changes require migration scripts and downtime | Semi-structured: rigid per-application schema, limited extensibility |
| Relationship Modeling | First-class typed relationships (OWL ObjectProperties); traversable at query time | Foreign key joins; relationship queries require complex multi-table SQL | Application-level joins; cross-domain relationships not natively supported |
| Semantic Reasoning | OWL reasoning: infer new facts from axioms (e.g., subclass inference, property chains) | None: relational databases perform no semantic inference | None: application logic only |
| Query Language | SPARQL 1.1: graph patterns, property paths, federated queries | SQL: set-based, optimized for aggregate queries on structured tables | Proprietary API or SQL variant; limited ad-hoc query capability |
| Multi-System Integration | Native: entities from multiple systems represented as co-referenced graph nodes | Via ETL pipelines: data physically copied between systems | Limited: typically integrates with one ERP and one SCADA system |
| AI Readiness | High: graph structure is natural input for graph neural networks and RAG LLM patterns | Moderate: tabular data requires feature engineering for ML models | Low: semi-structured, application-specific data requires heavy transformation |
| Standards Basis | W3C RDF/OWL/SPARQL, ISA-95, ISO 15926, SAREF4INMA | Vendor-proprietary schemas (SAP HANA, Oracle DB); partial ISA-95 alignment | ISA-95 B2MML XML; vendor-proprietary execution models |

## 6.4 Real-World Manufacturing Knowledge Graph Examples

The Siemens Industrial Knowledge Graph is one of the most mature examples of enterprise manufacturing semantic modeling, integrating product lifecycle data (from Teamcenter PLM), plant maintenance data (from SAP PM), and production operations data using OWL ontologies and SPARQL query interfaces. Siemens has used this knowledge graph to enable cross-domain analytics — connecting design engineering, manufacturing process planning, and operational maintenance data in a single semantic model.

In the automotive sector, manufacturers including BMW and Volkswagen Group have developed ontology-based vehicle configuration graphs that manage the enormous complexity of automotive product variants. A modern vehicle may have tens of millions of valid configurations; managing the interdependencies between options, components, and production constraints is a natural graph problem addressed through OWL-based configuration ontologies and SPARQL constraint validation.

In pharmaceutical manufacturing, FDA Process Analytical Technology (PAT) frameworks have driven the development of batch record ontologies that connect batch production orders, equipment qualification records, analytical method validation data, and process parameter observations. These semantic models support both process understanding (understanding how process parameters affect product quality) and regulatory compliance (demonstrating batch-level traceability to FDA standards).

In aerospace and defense, AS9100-aligned process ontologies connect design data (from CATIA or NX CAD systems), manufacturing process plans (from DELMIA or Siemens NX CAM), and quality records into semantically integrated models that support first article inspection reporting, non-conformance traceability, and design change impact analysis.

# Section 7 — Semantic Layers in Manufacturing ERP and MES

## 7.1 The Semantic Layer in Manufacturing Analytics

A **semantic layer** is an abstraction layer — implemented in a BI platform, a data catalog, or a knowledge graph — that maps raw ERP and MES database tables to business-meaningful concepts, insulating analytics consumers from the underlying technical complexity of source system schemas. Without a semantic layer, manufacturing analytics requires deep ERP expertise: knowing, for example, that in SAP S/4HANA, "available inventory" is not a single field but must be calculated by joining material document tables (MSEG), stock tables (MARD, MCHB, MARC), and valuation tables (MBEWH) through complex logic that accounts for unrestricted stock, quality inspection stock, blocked stock, and in-transit stock.

With a semantic layer, a business analyst queries a single concept — "Available Inventory" — that the semantic layer resolves to the correct multi-table join for the specific ERP system in use. When the ERP system is upgraded or migrated, only the semantic layer mapping changes; all downstream analytics reports and dashboards continue to function. The semantic layer is thus both an integration simplifier and a change isolation mechanism.

In semantic model terms, the manufacturing semantic layer is expressed as a set of OWL classes and properties that correspond to business-meaningful concepts, with explicit mappings (R2RML rules or YARRRML specifications) to the underlying ERP and MES database tables that provide their data. The semantic layer can be queried through a SPARQL endpoint, a virtual knowledge graph (VKG) interface, or a BI semantic model (Power BI measures and dimensions, Tableau calculated fields) that translates user queries into the appropriate source system queries.

## 7.2 Key Manufacturing Semantic Layer Metrics and Dimensions

The following metrics and dimensions constitute the core semantic layer vocabulary for manufacturing analytics. Each is defined as a semantic model concept with its graph structure described.

**Overall Equipment Effectiveness (OEE)** is the product of three component factors: Availability (actual runtime divided by planned production time), Performance (actual output rate divided by ideal output rate), and Quality (good units produced divided by total units started). OEE is the primary KPI for manufacturing equipment productivity and benchmarks well against industry standards. In a semantic model, OEE is a *DerivedMeasure* class with ObjectProperties linking to Equipment, TimeInterval, ProductionRun, and three ComponentMeasure individuals (one each for Availability, Performance, and Quality). OEE calculation is expressed as a SPARQL CONSTRUCT query that aggregates SensorObservation and ProductionEvent individuals for a given equipment and time interval.

**On-Time Delivery (OTD)** is the percentage of customer orders delivered on or before the contractually committed delivery date. It is the primary external-facing supply chain performance metric. In the knowledge graph, OTD is computed by joining SalesOrder individuals (carrying the CommittedDeliveryDate DatatypeProperty) with ShipmentEvent individuals (carrying the ActualShipDate DatatypeProperty) via the *fulfilledBy* ObjectProperty.

**First Pass Yield (FPY)** is the percentage of units completing a manufacturing operation or process sequence without requiring rework, repair, or scrap — passing "first time, every time." FPY links QualityInspection individuals (carrying the inspectionResult DatatypeProperty) to ProductionOrder and OperationStep individuals via the *inspects* ObjectProperty. Aggregating FPY across operations reveals the steps with the highest non-conformance rates — the primary input to Six Sigma improvement projects.

**Inventory Turns** is the ratio of Cost of Goods Sold to average inventory value over a period, measuring how efficiently inventory investment is being converted into revenue. A high inventory turns ratio indicates lean, efficient inventory management. In the knowledge graph, Inventory Turns joins FinancialLedgerEntry individuals (accumulating COGS) with ValuatedStockSnapshot individuals (recording inventory values at period intervals).

**Schedule Adherence** measures the degree to which actual production follows the planned production schedule — the percentage of planned production orders completed at their scheduled quantity and on their scheduled date. It is computed by comparing PlannedOrder individuals (planned quantity and date) with ProductionOrder individuals (actual quantity confirmed and actual completion date) via the *executedAs* ObjectProperty.

**Capacity Utilization** is the ratio of actual output (measured in standard hours) to available capacity (also in standard hours) at a work center over a planning period. It measures how effectively a work center's productive capacity is being used. In the semantic model, Capacity Utilization is computed from ActualTimeConfirmation individuals (actual hours per operation) against WorkCenter capacity definitions, linked through the *confirmedAt* and *performedBy* ObjectProperties.

## 7.3 ISA-95 as the Semantic Layer Foundation for MES

ISA-95 Part 2 provides eight canonical object models that together define the complete operational information domain of a manufacturing facility: Production Operations Management, Maintenance Operations Management, Quality Operations Management, Inventory Operations Management, and their associated definitions of Personnel, Equipment, Material, and Process Segment. These eight object models constitute the natural semantic layer for MES data integration.

| ◈ ISA-95 as Semantic Layer: The B2MML Bridge B2MML (Business to Manufacturing Markup Language) is the W3C XML Schema implementation of the ISA-95 object models — the XML serialization of ISA-95 concepts used for MES-to-ERP data exchange. B2MML XML documents are directly mappable to RDF triples using R2RML or YARRRML mapping rules, making B2MML the practical bridge between legacy MES XML interfaces and modern knowledge graph architectures. The mapping from B2MML to RDF is conceptually straightforward: B2MML XML elements become RDF subject URIs; B2MML attributes become RDF DatatypeProperty literals; B2MML nested elements become RDF ObjectProperty links to child individuals. This mapping can be implemented in standard RDF mapping frameworks (Ontop, Morph-KGC, YARRRML) without modification to source MES systems, enabling semantic layer construction from existing ISA-95-compliant MES interfaces. |
| --- |

The ISA-95 **Process Segment** class is particularly important for manufacturing semantic layer construction. A Process Segment represents a grouping of personnel, equipment, and material resources required to perform a segment of a manufacturing process. It is the ISA-95 equivalent of the routing operation — the semantic unit that links production scheduling (which segments are needed, in what sequence) to resource management (which personnel, equipment, and materials are required). Encoding Process Segments as SKOS Concepts within a ConceptScheme provides the controlled vocabulary for production scheduling communications between ERP and MES systems.

# Section 8 — Semantic Modeling Patterns for Manufacturing

The following six canonical patterns represent the primary implementation approaches for manufacturing semantic models, organized by entry point (where the modeling effort begins) and primary use case. Most enterprise implementations combine elements of multiple patterns.

## 8.1 Pattern 1 — ISA-95 Ontology-First (Top-Down)

In the ISA-95 Ontology-First pattern, the implementation begins by adopting the ISA-95 Part 1 and Part 2 object models as the foundational OWL class hierarchy, and then mapping source system data (ERP, MES, SCADA) to the ISA-95 class structure. This top-down approach ensures full alignment with the international standard from the outset.

**Core OWL Classes:** PersonnelClass, EquipmentClass, MaterialClass, ProcessSegment, ProductionRequest (the ERP-to-MES production schedule), ProductionResponse (the MES-to-ERP actual execution confirmation), WorkMaster (the process definition — equivalent to a routing), WorkDefinition (the scheduled instance — equivalent to a planned operation).

This pattern is best suited for: MES-to-ERP integration projects; manufacturing operations management systems requiring regulatory compliance documentation; and organizations that need to exchange manufacturing data with external partners using ISA-95-compliant interfaces. The primary risk is scope: ISA-95 is a comprehensive standard covering all aspects of manufacturing operations, and implementation teams must carefully bound the scope to avoid attempting a full ISA-95 implementation in a single project.

## 8.2 Pattern 2 — Product Taxonomy-First (Bottom-Up)

The Product Taxonomy-First pattern begins with the construction of a SKOS product taxonomy — aligned to an external standard (eCl@ss or UNSPSC) or developed internally — as the controlled vocabulary for finished goods, components, and materials. Ontological complexity is added incrementally: first BOM relationships (hasPart ObjectProperties), then supplier relationships (suppliedBy ObjectProperties), then routing linkages (hasRouting ObjectProperties).

This bottom-up approach delivers early value in procurement analytics and product master data management — domains where a well-structured product taxonomy alone generates significant analytical capability — before the full ontological investment is made. It is well-suited for organizations whose most pressing integration problem is in procurement or product data management rather than production execution. Recommended tooling includes PoolParty Semantic Suite or TopBraid EDG with eCl@ss import connectors.

## 8.3 Pattern 3 — Hybrid BOM + Routing Graph (Most Common in Practice)

The Hybrid BOM + Routing Graph pattern is the most commonly implemented approach in industrial manufacturing semantic model projects. It models the Bill of Materials as an OWL-based component graph (using hasPart, quantityOf, and effectiveFrom properties) and models the routing as an ordered sequence of OWL Operation individuals linked by hasNextOperation ObjectProperties. The BOM and routing graphs are connected via an associatedOperation ObjectProperty linking each MaterialComponent individual (in the BOM graph) to the Operation individuals (in the routing graph) that consume it.

This pattern supports a rich set of downstream applications: production planning engines can use SPARQL queries to perform BOM explosion and generate material requirements; digital twin platforms link ProductionOrder individuals to both BOM and routing graphs for process simulation; root cause analysis traverses from QualityInspection events through the routing to the specific Operation and WorkCenter where the defect was produced, and from there through the BOM to the specific MaterialBatch consumed. A representative example: a "Widget Assembly" ProductionOrder individual links to a BOM graph (10 component individuals across 3 BOM levels) plus a Routing graph (5 Operation individuals across 3 WorkCenter individuals) plus a set of QualityInspection event individuals — all traversable in a single connected SPARQL query.

## 8.4 Pattern 4 — Equipment and Maintenance Ontology

The Equipment and Maintenance Ontology pattern models physical manufacturing assets as OWL individuals of the EquipmentClass, with DatatypeProperties for serial number, manufacturer, model, installation date, and rated capacity, and ObjectProperties linking to Location (within the ISA-95 hierarchy), Manufacturer, and MaintenanceWorkOrder individuals. A FMEA (Failure Mode and Effects Analysis) taxonomy is modeled as a SKOS ConceptScheme, with FailureMode Concepts linked to Equipment individuals via a hasKnownFailureMode ObjectProperty.

Sensor data streams from IIoT platforms are linked via SAREF4INMA FeatureOfInterest and Observation classes, connecting each SensorObservation individual (a specific temperature, vibration, or pressure reading at a specific timestamp) to the Equipment individual it characterizes. This connected structure enables predictive maintenance models — machine learning algorithms that consume the graph-structured feature set of equipment observations, maintenance history, and failure mode knowledge — to predict remaining useful life and trigger preventive maintenance work orders.

This pattern is particularly important for pharmaceutical manufacturing (equipment qualification and validation records must be traceable to specific maintenance events and calibration certificates), aerospace (airworthiness maintenance records), and semiconductor manufacturing (equipment certification for specific process specifications).

## 8.5 Pattern 5 — Supply Chain and Supplier Ontology

The Supply Chain and Supplier Ontology pattern models the external supply chain as an extension of the internal manufacturing knowledge graph. Supplier, SupplierSite, PurchasingContract, and DeliveredMaterial are modeled as OWL classes. Each Supplier individual is linked to the MaterialClass individuals it supplies via the suppliesMaterial ObjectProperty, and to PurchasingContract individuals via the governedBy ObjectProperty. Delivery performance — actual lead times, on-time delivery rates, quality reject rates — is accumulated through DeliveryEvent individuals linked to PurchaseOrder individuals.

Supply risk classifications (geopolitical risk, financial stability risk, single-source risk, geographic concentration risk) are encoded as a SKOS taxonomy aligned to standard supply chain risk frameworks. External authority data is linked via owl:sameAs assertions to D&B (Dun & Bradstreet) company identifiers and GS1 GLN (Global Location Numbers), enabling enrichment from external data sources and multi-enterprise supply chain interoperability. This pattern is foundational for ESG (Environmental, Social, Governance) supply chain reporting — tracing carbon emissions, labor practices, and material provenance through the supplier graph.

## 8.6 Pattern 6 — Quality and Non-Conformance Ontology

The Quality and Non-Conformance Ontology pattern models the quality management domain as a formal semantic structure. QualityInspection, NonConformanceReport, DefectType, CorrectiveActionReport, and PreventiveActionRecord are defined as OWL classes. DefectType is organized as a SKOS taxonomy (Visual Defects → Surface Defects → Scratch, Dent, Discoloration; Dimensional Defects → Out-of-Tolerance → Over-Tolerance, Under-Tolerance) enabling hierarchical defect classification for statistical quality analysis.

Each NonConformanceReport individual is linked to its causal ProductionOrder, Operation, WorkCenter, Equipment, and MaterialBatch via provenance ObjectProperties, creating a complete quality lineage graph. Corrective actions are linked to their triggering NCRs and to the downstream process changes they produced, enabling effectiveness measurement. This pattern directly supports Six Sigma DMAIC projects (where defect data analysis drives Define, Measure, Analyze steps), ISO 9001 quality management system compliance, AS9100 aerospace quality documentation, and FDA 21 CFR Part 11 electronic records compliance in pharmaceutical manufacturing.

## 8.7 Governance and Stewardship for Manufacturing Semantic Models

Semantic models are strategic data assets that require structured governance to remain accurate, consistent, and aligned with evolving manufacturing operations. Effective governance assigns clear stewardship roles:

- **Data Architect:** responsible for ontology design, OWL class hierarchy decisions, property definitions, and alignment to external standards (ISA-95, eCl@ss, SKOS)
- **Domain Subject Matter Expert (SME):** shop-floor engineers, process engineers, and production planners who validate that semantic model concepts accurately reflect operational reality
- **ERP/MES Systems Analyst:** responsible for maintaining source-system-to-ontology mapping rules (R2RML, YARRRML) as ERP and MES systems are upgraded
- **Taxonomy Manager:** responsible for the controlled vocabulary layer — adding new SKOS concepts, managing prefLabel/altLabel consistency, and synchronizing with external taxonomy updates (new UNSPSC releases, eCl@ss version updates)

Engineering Change Notice (ECN) management is a critical governance challenge: when a BOM is revised, the semantic model must capture the change as a versioned event — a ChangeEvent individual linked to the superseded and replacement BOM relationships, with effective-date DatatypeProperties enabling time-bounded BOM queries. This temporal versioning capability — representing the BOM as it was at any past point in time — is a significant advantage of semantic graph representation over relational ERP BOM schemas, which typically carry only the current BOM state.

Master Data Management (MDM) integration connects the manufacturing ontology to the enterprise MDM hub: the Material Master (which defines all manufactured and purchased materials), the Equipment Master (which defines all physical assets), and the Supplier Master (which defines all external supply partners). The manufacturing ontology serves as the semantic backbone of the MDM hub — the formal definition of what "Material," "Equipment," and "Supplier" mean — while the MDM hub provides the operational governance workflow for master data creation, enrichment, and lifecycle management.

# Section 9 — Digital Twins and Industry 4.0 Semantic Terminology

## 9.1 Digital Twin Terminology in Semantic Models

**Digital Twin** is a virtual, semantically annotated representation of a physical asset, process, or system that is bidirectionally synchronized with real-world operational data. In manufacturing, digital twins exist at multiple scales: asset twins (representing individual machines or tools), process twins (representing manufacturing processes), line twins (representing production lines), and plant twins (representing entire manufacturing facilities). Each scale of twin requires a corresponding level of semantic model detail — from individual sensor observations (asset twins) to aggregated production KPIs and supply chain connections (plant twins).

| ◆ Digital Twin OWL Model Pattern In a semantic model, DigitalTwin is an OWL class with the isRepresentationOf ObjectProperty linking the digital twin individual to its PhysicalAsset counterpart. The hasCurrentState ObjectProperty links to a StateObservation individual (the most recent synchronized state). The hasHistoricalState ObjectProperty links to the time-ordered sequence of past StateObservation individuals, enabling temporal queries over the twin's state history. The conformsToModel ObjectProperty links the DigitalTwin to its defining SimulationModel individual (the physics-based or data-driven model used to predict behavior), while observedBy links to the set of SensorObservation individuals that provide synchronization data. This connected structure is the semantic backbone that transforms a collection of sensor readings and model outputs into a coherent, queryable digital representation of a physical manufacturing asset. |
| --- |

**Asset Administration Shell (AAS)** is the Industry 4.0 standard (IEC 63278) for digital twin information models, defined by the Industrial Digital Twin Association (IDTA) and Platform Industry 4.0. An AAS consists of an Asset (the physical thing being represented) and a set of Submodels (structured information containers each covering a specific aspect of the asset — nameplate data, technical properties, operational data, maintenance history). The AAS submodel structure maps directly to OWL class and datatype property definitions, making AAS a practically important bridge between Industry 4.0 industrial standards and semantic web formalisms.

**Cyber-Physical System (CPS)** is an engineered system in which computational processes and physical processes are tightly integrated and mutually influencing — the physical process affects computation (via sensor inputs), and computation affects the physical process (via actuator outputs). Manufacturing CPSs include CNC machine tools (where cutting parameters are continuously computed and adjusted based on force and vibration sensor feedback), additive manufacturing systems (where build parameters are adjusted layer-by-layer based on in-process quality monitoring), and smart assembly systems (where robot paths are continuously optimized based on part position sensing).

**Industrial IoT (IIoT)** is the application of Internet of Things technologies — sensors, wireless connectivity, edge computing, and cloud platforms — to industrial manufacturing environments. IIoT generates the high-frequency sensor event streams (temperature, pressure, vibration, energy consumption, cycle count) that populate digital twin knowledge graphs with real-time operational data. The semantic challenge of IIoT is the contextualization problem: a raw sensor reading (e.g., 72.3°C at sensor tag ML-COMP-04-T01) becomes manufacturing knowledge only when contextualized with what asset it measures, what that asset is doing, what product it is processing, and what the normal operating range is — a contextualization that the manufacturing knowledge graph provides.

## 9.2 Industry 4.0 Standards and Their Semantic Relevance

**RAMI 4.0 (Reference Architectural Model Industry 4.0)** is a three-dimensional framework defined by the German industry consortium ZVEI/VDI/BITKOM that maps Industry 4.0 concepts along three axes: the Life Cycle & Value Stream axis (from product type definition through product instance to end-of-life), the Hierarchy Levels axis (from product component through factory to connected world), and the Layers axis (from physical assets through integration and communication to functional and business layers). Semantic models — ontologies, taxonomies, and knowledge graphs — sit primarily at the Information Layer of RAMI 4.0, providing the structured data representations that enable the higher functional and business layers to operate on manufacturing knowledge rather than raw data.

**OPC UA (OPC Unified Architecture)** is the IEC 62541 communication and information modeling standard for industrial automation. OPC UA's Information Model component (expressed as OPC UA NodeSets) defines the semantic structure of data exposed by industrial devices and systems — the types, relationships, and properties of the information objects an OPC UA server makes available to clients. OPC UA NodeSets are mappable to OWL ontologies, and several research and industrial initiatives have produced formal mappings between OPC UA companion specifications (for robotics, machine tools, and plastic machinery) and OWL representations. OPC UA thus serves as both the communication protocol and the information model standard for IIoT data that feeds manufacturing knowledge graphs.

**AutomationML** is an XML-based data format (IEC 62714) for the exchange of engineering data between planning, simulation, and automation tools. AutomationML encodes plant topology, kinematics, logic, and communication data in a format that is mappable to RDF for semantic integration. AutomationML-to-RDF converters have been published in research literature, enabling the rich engineering context of AutomationML plant models to become part of the manufacturing knowledge graph alongside operational data from OPC UA and B2MML sources.

**ECLASS** is a product classification and description standard built on IEC 61360 property semantics, developed by the ECLASS organization with strong participation from German manufacturing industry. ECLASS provides machine-readable property definitions — with formal data types, units of measure, and value ranges — for over one million product properties organized into a four-level product hierarchy. ECLASS is particularly important for equipment and component semantic modeling: ECLASS property definitions provide the vocabulary for OWL DatatypeProperty alignments that enable comparison and interoperability of product data across manufacturer and customer systems.

# Section 10 — Tool Landscape for Manufacturing Semantic Models

## 10.1 Ontology and Taxonomy Authoring Tools

| Tool | Type | Primary Use in Manufacturing | Key Strengths |
| --- | --- | --- | --- |
| Protégé (Stanford) | Open-source OWL ontology editor | ISA-95, FMEA, and equipment ontology authoring; academic and research contexts | Full OWL 2 support; free; active community; Pellet and HermiT reasoner plugins |
| TopBraid EDG | Enterprise semantic modeling platform | Pharmaceutical and aerospace manufacturing master data ontologies; SKOS + OWL + SHACL governance | Enterprise workflow; data quality (SHACL); eCl@ss import; REST API integration |
| PoolParty Semantic Suite | SKOS-first taxonomy management | Product taxonomy management; NLP-driven auto-classification of technical content; knowledge graph construction | Strong SKOS/OWL hybrid; NLP integration; multilingual support; Linked Data publishing |
| Semaphore (OpenText) | Enterprise taxonomy and metadata management | Defense and aerospace supply chain semantic integration; technical document classification | Strong classification engine; integration with OpenText content management; aerospace sector adoption |

## 10.2 Graph Databases for Manufacturing Knowledge Graphs

**Stardog** is an enterprise RDF triple store with OWL reasoning, virtual knowledge graph (VKG) capabilities, and a SPARQL 1.1 endpoint. Stardog's virtual knowledge graph feature enables SPARQL queries to be answered by querying relational ERP databases in real time — without physically moving data into the graph store — making it particularly well-suited for manufacturing semantic layer construction over existing SAP and Oracle databases.

**GraphDB (Ontotext)** is a SPARQL 1.1 compliant RDF triple store with OWL reasoning and full-text search capabilities. GraphDB is widely used in smart factory semantic integration projects, particularly in European Industry 4.0 research consortia. Its connector framework supports data ingestion from relational databases, REST APIs, and Kafka event streams — covering the primary data sources in a manufacturing enterprise integration architecture.

**Neo4j** is the most widely deployed property graph database, using the Cypher query language rather than SPARQL. Neo4j lacks native OWL reasoning but supports semantic plugins and has been widely used for manufacturing supply chain graphs and quality traceability networks where the graph traversal capabilities and developer ecosystem outweigh the need for formal ontological reasoning. Neo4j's APOC and GDS (Graph Data Science) libraries provide graph algorithm capabilities — centrality, community detection, path finding — that are directly applicable to supply chain network analysis.

**Amazon Neptune** is a fully managed cloud graph database supporting both RDF/SPARQL (for ontology-based knowledge graphs) and property graph/Gremlin (for operational data graphs). Neptune is used in cloud-native manufacturing digital twin platforms on AWS, where it serves as the semantic integration layer connecting AWS IoT, AWS S3 data lakes, and SAP on AWS deployments. Neptune's fully managed nature eliminates graph database infrastructure management overhead for cloud-native manufacturing architectures.

**ArangoDB** is a multi-model graph database supporting document, graph, and key-value data models with a unified AQL (ArangoDB Query Language). Its multi-model capability makes it well-suited for manufacturing operational data integration scenarios where some data is naturally document-structured (production order details in JSON), some is naturally graph-structured (equipment topology and BOM relationships), and some requires key-value access patterns (real-time sensor readings).

## 10.3 ERP-Integrated Semantic Platforms

**SAP Knowledge Graph (SAP Business Technology Platform)** is an emerging RDF/OWL-based product from SAP that connects SAP S/4HANA material master, equipment master, maintenance work order, and production order data through a graph layer exposed via SPARQL queries. Announced and progressively released from 2022 onward, the SAP Knowledge Graph represents the ERP vendor's recognition that semantic graph capabilities are required for AI-driven manufacturing applications — particularly for grounding LLM responses about SAP ERP data with factual, structured context.

**Oracle Semantic Technologies (Oracle Database)** provides a native RDF quad store within the Oracle Database engine, enabling RDF triple storage, OWL reasoning, and SPARQL queries alongside conventional SQL queries within a single Oracle Database instance. Manufacturing companies standardized on Oracle ERP and Oracle Database can leverage this capability to build semantic layers over their existing Oracle manufacturing schemas without deploying a separate graph database.

**Microsoft Azure Purview / Microsoft Fabric** provide data catalog and semantic layer services that integrate with manufacturing data from Microsoft Dynamics 365 (ERP and Field Service), Azure IoT Hub (IIoT sensor data), and Azure Digital Twins (digital twin platform). Microsoft Fabric's semantic model capabilities (built on Power BI's semantic layer engine) provide a business-user-accessible semantic layer for manufacturing analytics, while Azure Purview provides the data catalog and lineage tracking that governs how manufacturing data assets are documented, classified, and governed across the enterprise.

# Section 11 — Reference Architecture: Manufacturing Semantic Model

The following layered reference architecture describes a complete, production-grade manufacturing semantic model infrastructure. Each layer is described with its constituent components, its primary function, and its interface to adjacent layers. This architecture is technology-agnostic at the platform level — the patterns apply whether the graph database is Stardog or Neptune, the ERP is SAP or Oracle, and the MES is Siemens OPCENTER or Rockwell FactoryTalk.

| LAYER 1 — Raw Data Sources |
| --- |

The foundation of the architecture is the set of source systems that generate manufacturing operational data. These include: **SAP S/4HANA** (material master, BOM, routing, production order, cost center, and financial data in HANA in-memory tables); **Oracle Cloud Manufacturing** (discrete jobs, BOMs, routings, WIP transactions); **MES platforms** (Siemens OPCENTER, Rockwell FactoryTalk, AVEVA MES — production execution events, work order dispatching, genealogy records, quality inspection results); **SCADA historians** (OSIsoft PI, AVEVA System Platform — time series sensor data for temperature, pressure, vibration, energy consumption, cycle counts); **PLM systems** (Siemens Teamcenter, PTC Windchill — engineering BOMs, product structures, CAD metadata, engineering change notices); and **IIoT sensor streams** (MQTT, OPC UA, REST APIs from smart sensors, edge gateways, and IoT platforms).

| LAYER 2 — Data Integration |
| --- |

The data integration layer transforms source system data into RDF triples using semantic mapping rules. Components include: **ETL pipelines** with R2RML or YARRRML mapping rules that translate ERP relational table records into RDF triple sets; **OPC UA adapters** that subscribe to OPC UA server data changes and generate SAREF4INMA Observation individuals in real time; **B2MML XML parsers** that transform ISA-95-compliant MES XML messages into ISA-95 OWL class instances; and **REST API connectors** that retrieve JSON data from cloud manufacturing platforms and map to ontology individuals using JSON-LD context documents. The integration layer is responsible for URI generation (assigning globally unique identifiers to each individual), deduplication (identifying when records from different source systems refer to the same real-world entity), and temporal stamping (recording the provenance and timestamp of each triple assertion).

| LAYER 3 — SKOS Taxonomy Layer |
| --- |

The taxonomy layer provides the controlled vocabularies that classify and label manufacturing entities consistently across systems. It comprises: a **Product Taxonomy** encoded as a SKOS ConceptScheme aligned to eCl@ss and UNSPSC, covering finished goods, components, raw materials, and indirect materials; a **Work Center Type Taxonomy** classifying work centers by capability category for capacity planning; an **Operation Type Taxonomy** organizing manufacturing operations into a hierarchy for routing design and cost classification; a **Defect Taxonomy** structured hierarchically for quality management and Six Sigma analytics; and a **Supplier Classification Taxonomy** encoding supplier categories, risk tiers, and commodity groups. Each taxonomy concept carries skos:prefLabel, skos:altLabel, skos:notation, and skos:scopeNote annotations to support both human governance and machine processing.

| LAYER 4 — OWL Ontology Layer |
| --- |

The ontology layer defines the formal schema of the manufacturing knowledge graph. It is organized into modular ontology files covering: the **ISA-95 Core Ontology** (Enterprise, Site, Area, WorkCenter, WorkUnit, PersonnelClass, EquipmentClass, MaterialClass, ProcessSegment); the **BOM Ontology** (ManufacturedItem, PurchasedItem, hasPart, quantityOf, effectiveFrom, effectiveTo, modifiedByECN); the **Routing Ontology** (Routing, Operation, hasNextOperation, performedAt, setupTime, runTime); the **Equipment Ontology** (Equipment, hasManufacturer, hasModel, hasSerialNumber, hasLocation, hasMaintenanceHistory); and the **Quality Ontology** (QualityInspection, NonConformanceReport, DefectType, CorrectiveAction, hasDefectType, inspects). SHACL constraint shapes validate data quality on each ontology class, enforcing required properties and value constraints before triples are committed to the knowledge graph.

| LAYER 5 — Manufacturing Knowledge Graph |
| --- |

The manufacturing knowledge graph is the integrated entity store — the operational realization of the ontology layer populated with actual production data from source systems. It stores: production orders linked to their BOM graph (component individuals and hasPart relationships), routing graph (operation individuals and hasNextOperation relationships), equipment assignments (performedAt WorkCenter individuals), personnel records (executedBy PersonnelClass individuals), quality inspection events (QualityInspection individuals linked to specific operations and material batches), and digital twin representations (DigitalTwin individuals linked to physical equipment and their sensor observation histories). The knowledge graph exposes a SPARQL 1.1 endpoint for query access, a REST API for application integration, and an OWL reasoning service for inference-based query answering.

| LAYER 6 — Application Layer |
| --- |

The application layer delivers manufacturing intelligence to operational and analytical consumers through: **OEE dashboards** (SPARQL-backed real-time equipment effectiveness monitoring); **predictive maintenance AI** (graph neural networks and time series models consuming equipment and sensor knowledge graph features); **root cause analysis tools** (interactive graph traversal from quality events through process, equipment, and material provenance); **digital twin visualization** (3D/2D plant models synchronized to knowledge graph state through the DigitalTwin class); **LLM-based manufacturing assistant** (RAG architecture grounding natural language queries in SPARQL-retrieved knowledge graph facts to prevent hallucination); and **supply chain risk monitoring** (supplier graph traversal identifying at-risk components and alternative sourcing paths).

The data flow that illustrates the architecture's value: a quality engineer notices elevated reject rates on a product line and initiates a root cause analysis query through the application layer. The query traverses the SPARQL endpoint into the knowledge graph, following QualityInspection individuals (that recorded the defects) through the *inspects* ObjectProperty to the ProductionOrder, through the *hasOperation* ObjectProperty to the specific Operation and WorkCenter where the defect was produced, through the *performedBy* ObjectProperty to the Equipment individual (Machine MC-042), through the *hasMaintenanceHistory* ObjectProperty to confirm the last maintenance event was 47 days ago (past the 30-day service interval), and through the *consumedMaterial* ObjectProperty to the MaterialBatch (Lot B22-4471 from Supplier Acme Metals). The complete causal chain — deferred maintenance on a specific machine processing a specific material batch — is returned in a single connected graph traversal that would have required five separate database queries across three systems in a conventional architecture.

# Section 12 — Conclusion and Recommendations

Manufacturing enterprises stand at a structural inflection point. The proliferation of digital systems — ERP, MES, SCADA, PLM, IIoT platforms, digital twin engines — has generated unprecedented volumes of operational data while simultaneously deepening the terminological fragmentation that prevents that data from becoming organizational knowledge. The same industrial reality — a production order, a work center, a material batch, a quality inspection — exists in multiple systems under multiple names with multiple data representations, creating integration friction, analytics failures, and AI implementation barriers that cannot be resolved by yet more ETL pipelines and API contracts.

Semantic models — built on the proven foundation of RDF, OWL, SKOS, and established manufacturing standards (ISA-95, eCl@ss, SAREF4INMA, ISO 15926) — provide the structural solution. By formally defining what manufacturing concepts mean — not just what they are named in a specific system — semantic models enable integration at the level of shared understanding rather than shared data format. The manufacturing knowledge graph, populated through semantic mapping from source systems, provides a connected, traversable, reasoning-capable representation of the manufacturing enterprise that enables root cause analysis, predictive maintenance, digital twin synchronization, supply chain visibility, and AI grounding in a unified architecture.

This document has provided a comprehensive reference of the terminology, standards, patterns, and tools that practitioners need to design, implement, and govern manufacturing semantic models. The following five recommendations distill the practical imperatives for organizations beginning or advancing their semantic manufacturing initiatives.

## Five Actionable Recommendations

- **Adopt ISA-95 as your foundational semantic layer for MES and ERP integration before designing custom ontology classes.** ISA-95 Part 1 and Part 2 provide a formally defined, internationally recognized class hierarchy for manufacturing operations management data that has been validated across thousands of real-world implementations. Custom classes built on this foundation inherit its interoperability credentials; custom classes built without it must be manually mapped to it later — at significant cost. Start with ISA-95 and extend; do not attempt to replace it.
- **Encode your product taxonomy using SKOS aligned to eCl@ss or UNSPSC to achieve procurement and PLM interoperability.** Product master data is the most widely shared data category across manufacturing enterprise systems — from ERP material masters to MES work order materials to PLM product structures to supplier catalog items. A SKOS product taxonomy aligned to an external standard provides the semantic backbone for cross-system product data alignment, enabling procurement analytics, catalog rationalization, and supply chain interoperability that internal coding structures alone cannot deliver.
- **Model your Bill of Materials as a semantic graph from day one.** The BOM is the most central data structure in discrete manufacturing, and its representation as a semantic graph (OWL individuals connected by hasPart ObjectProperties with quantity and effectiveDate annotations) unlocks three high-value capabilities immediately: MRP-equivalent material requirements calculation via SPARQL recursive traversal, digital twin linkage (connecting the virtual twin's component model to the actual BOM graph), and quality traceability (traversing from a defective unit through its BOM to the specific material batch responsible). The investment in semantic BOM modeling pays dividends across production planning, quality, and digital twin domains simultaneously.
- **Govern manufacturing terminology as a strategic master data asset — assign taxonomy and ontology stewardship roles to domain SMEs, not just IT.** The primary failure mode of manufacturing semantic model projects is ontological drift: the formal model diverges from operational reality as manufacturing processes, products, and systems evolve without corresponding model updates. Preventing drift requires governance structures that involve shop-floor engineers, production planners, and quality managers as active stewards of the semantic model — not as occasional reviewers of IT-delivered documentation. Formal stewardship roles, change management processes for ECN-driven BOM updates, and regular domain-expert review cycles are non-negotiable governance requirements.
- **Align your manufacturing knowledge graph to external authority sources to enable multi-enterprise supply chain semantics.** The full value of a manufacturing knowledge graph is realized when it connects to the external world — suppliers, customers, regulatory authorities, and logistics networks. Linking Supplier individuals to D&B DUNS identifiers, linking Material individuals to GS1 GTINs and GLNs, and linking Equipment individuals to manufacturer ECLASS codes enables the knowledge graph to participate in multi-enterprise data exchanges, federated SPARQL queries across supply chain partners, and enrichment from external data sources (D&B financial risk scores, GS1 product databases, regulatory authority product registries). External authority alignment transforms an internal semantic model into a node in a global manufacturing knowledge network.

The convergence of semantic web standards, Industry 4.0 industrial standards, and AI-driven manufacturing applications creates a unique implementation window for manufacturing organizations prepared to invest in semantic infrastructure. Those that establish robust, governed, standards-aligned manufacturing semantic models in this period will hold structural advantages in production agility, supply chain resilience, and AI-enabled operational intelligence that will define competitive differentiation in advanced manufacturing through the remainder of this decade.

# Glossary of Manufacturing and Semantic Modeling Terms

The following terms are defined in alphabetical order as used in manufacturing environments and semantic model implementations. Terms marked with (★) are foundational to semantic model design.

**Asset Administration Shell (AAS)** — The Industry 4.0 standard (IEC 63278) information model for digital twins. An AAS consists of an Asset identifier and a set of Submodels, each covering a defined aspect of the asset (nameplate, technical properties, maintenance data). AAS submodel structure is directly mappable to OWL class and property definitions.

**Available Capacity** — The total productive capacity a work center can deliver in a planning period, calculated from shift schedules, planned downtime, and efficiency ratings. The supply side of the capacity planning equation.

**Bill of Materials (BOM) ★** — A hierarchical, structured list of all components, sub-assemblies, and raw materials required to produce one unit of a parent item, with quantities and units of measure specified at each level. The foundational product structure data object in manufacturing, naturally represented as a directed acyclic graph in semantic models.

**B2MML (Business to Manufacturing Markup Language)** — The W3C XML Schema implementation of ISA-95 object models, used for MES-to-ERP data exchange. B2MML XML documents are mappable to RDF triples via R2RML or YARRRML mapping rules.

**Capacity Requirements Planning (CRP)** — The detailed calculation of work center capacity loads derived from MRP planned orders and production routings, performed after MRP explosion to validate resource feasibility.

**Cyber-Physical System (CPS)** — An engineered system in which computational and physical processes are tightly integrated, with each influencing the other through continuous sensing and actuation feedback loops.

**Demonstrated Capacity** — Actual historical capacity delivered by a work center over a representative past period, accounting for real-world inefficiencies. Used to set realistic capacity planning parameters in contrast to theoretical rated capacity.

**Digital Twin ★** — A virtual, semantically annotated representation of a physical asset, process, or system that is bidirectionally synchronized with real-world operational data. In OWL models, represented as a class with ObjectProperties linking to its PhysicalAsset counterpart, current StateObservation, and defining SimulationModel.

**eCl@ss** — An ISO 13584- and IEC 61360-compliant product classification and property description standard widely used in manufacturing for product master data management. Supports both SKOS taxonomy encoding and OWL property alignment.

**Engineering Change Notice (ECN)** — A formal document authorizing a change to the design of a product, its BOM, or its manufacturing process. In semantic models, ECNs are ChangeEvent individuals linked to superseded and replacement BOM relationships with effective-date temporal annotations.

**Failure Mode and Effects Analysis (FMEA)** — A systematic methodology for identifying potential failure modes of a product or process, their effects, and their causes, used in quality engineering and predictive maintenance. FMEA failure mode taxonomies are encoded as SKOS ConceptSchemes in manufacturing knowledge graphs.

**Firm Planned Order (FPO)** — A planned order that has been manually confirmed and locked by a planner, protecting it from automatic rescheduling by the MRP engine in subsequent planning runs.

**First Pass Yield (FPY)** — The percentage of units completing a manufacturing process step or sequence without requiring rework, repair, or scrap. A primary quality performance metric linking QualityInspection, ProductionOrder, and OperationStep in semantic models.

**Gross Requirements** — Total demand for a component from all parent item production orders across all time buckets in the MRP planning horizon, before offsetting with available inventory and scheduled receipts.

**Industrial IoT (IIoT)** — The application of Internet of Things sensing, connectivity, and cloud analytics technologies to industrial manufacturing environments, generating the sensor event streams that populate manufacturing knowledge graphs with real-time operational data.

**ISA-95 / IEC 62264 ★** — The international standard for enterprise-control system integration, defining a hierarchical equipment model (Enterprise→Site→Area→Work Center→Work Unit) and comprehensive manufacturing operations management data models. The primary reference standard for MES semantic model construction and the de facto ontological foundation for manufacturing knowledge graphs.

**Lead Time** — The total elapsed time from order placement to receipt of ordered goods. For manufactured items, composed of queue time, setup time, run time, move time, and wait time. Used by MRP to offset planned order release dates from requirement dates.

**Lot Sizing** — The policy rule applied by MRP to determine the quantity of each planned order. Common methods include Lot-for-Lot (LFL), Economic Order Quantity (EOQ), Fixed Order Quantity (FOQ), and Period Order Quantity (POQ).

**Manufacturing Execution System (MES)** — A software system at ISA-95 Level 3 that manages and tracks production execution on the shop floor, including work order dispatching, operation tracking, material consumption, genealogy recording, and quality data collection.

**Manufacturing Knowledge Graph ★** — An integrated, graph-structured knowledge base connecting products, processes, resources, orders, quality events, and supply chain entities through typed, semantically annotated OWL ObjectProperty relationships, queryable via SPARQL.

**Manufacturing Operations Management (MOM)** — The broader discipline encompassing all manufacturing operations: production operations management, quality operations management, inventory operations management, and maintenance operations management, as defined in the ISA-95 standard.

**Manufacturing Resource Planning (MRP II)** — An extension of MRP (developed by Oliver Wight in the 1980s) that integrates capacity requirements planning, shop-floor control, demand management, and financial simulation into a closed-loop manufacturing planning system.

**Master Production Schedule (MPS)** — A time-phased plan specifying which end items will be produced, in what quantities, and in which periods. The primary input to the MRP calculation engine.

**Material Requirements Planning (MRP)** — A computational engine developed by Joseph Orlicky that calculates time-phased component requirements by exploding a Master Production Schedule through the Bill of Materials, netting against available inventory and scheduled receipts.

**Net Requirements** — The uncovered demand for a component after subtracting on-hand inventory and scheduled receipts from gross requirements. Net requirements drive planned order generation in MRP.

**OEE (Overall Equipment Effectiveness)** — The product of Availability, Performance, and Quality ratios; the primary KPI for manufacturing equipment productivity. In semantic models, a DerivedMeasure class with ObjectProperties linking to Equipment, TimeInterval, ProductionRun, and component measure individuals.

**OPC UA (OPC Unified Architecture)** — IEC 62541; the communication and information modeling standard for industrial automation. OPC UA's Information Model (NodeSets) defines the semantic structure of industrial device data and is mappable to OWL ontologies.

**Pegging** — The MRP capability to trace a component net requirement back through the BOM hierarchy to its originating demand source (customer order or forecast). In semantic models, implemented as a SPARQL graph traversal through hasPart and dependsOnOrder ObjectProperties.

**Planned Order** — A system-generated recommendation by the MRP engine to manufacture or purchase a component quantity to satisfy net requirements. Not yet released to the shop floor or supplier; subject to planner review before release.

**Process Segment** — An ISA-95 class representing a grouping of personnel, equipment, and material resources required to perform a segment of a manufacturing process. The ISA-95 equivalent of a routing operation; used in production scheduling communications between ERP and MES systems.

**Production Order** — A formal authorization to manufacture a specified quantity of a product by a target date. Central hub entity in manufacturing knowledge graphs, connected to BOM, routing, equipment, personnel, and quality event individuals.

**RAMI 4.0** — The Reference Architectural Model Industry 4.0; a three-dimensional framework (Life Cycle × Hierarchy Levels × Layers) that positions semantic models at the Information Layer, providing the structured data representations for higher functional and business layers.

**Reorder Point** — The inventory level at which a replenishment order must be triggered, calculated as average demand during lead time plus safety stock. Relevant for min-max managed items; superseded by MRP time-phased planning for dependent-demand components.

**Rough-Cut Capacity Planning (RCCP)** — A high-level pre-MRP feasibility check of the Master Production Schedule against key resource capacities, using simplified resource profiles rather than detailed routings.

**Routing** — The defined sequence of operations, work centers, and time standards required to manufacture one unit of a product. In semantic models, represented as an ordered sequence of OWL Operation individuals linked by hasNextOperation ObjectProperties.

**SAREF4INMA** — The ETSI extension of the Smart Appliances Reference Ontology (SAREF) for Industry and Manufacturing, defining concepts for production batches, features of interest, and measurements applicable to IIoT manufacturing contexts.

**Safety Stock** — Buffer inventory maintained above expected demand to guard against demand variability or supply uncertainty. A quantity-based buffer expressed as units; distinct from Safety Lead Time (a time-based buffer).

**Semantic Layer ★** — An abstraction layer that maps raw ERP/MES database tables to business-meaningful concepts, enabling analytics consumers to query manufacturing knowledge without understanding source system schemas. Implemented via virtual knowledge graphs, R2RML mapping rules, or BI semantic model definitions.

**Shop Floor** — The physical area within a manufacturing facility where production operations are executed; the domain of MES systems and real-time operational event data. Corresponds to the Work Center and Work Unit levels of the ISA-95 equipment hierarchy.

**SKU (Stock Keeping Unit)** — The lowest-level unique identifier for a distinct product variant; the atomic unit of inventory management. In semantic models, typically a DatatypeProperty of the Product class linking to a specific product variant individual.

**UNSPSC** — The United Nations Standard Products and Services Code; a four-level hierarchical taxonomy (Segment→Family→Class→Commodity) for classifying products and services in procurement. Widely integrated in ERP purchasing modules and encodable as a SKOS ConceptScheme.

**Work Center** — A defined grouping of machines, tools, or labor resources used to perform specific manufacturing operations. The fundamental unit of capacity planning; an OWL class with properties for capacity, shift calendar, efficiency, and ISA-95 location hierarchy position.

**Work in Process (WIP)** — Partially manufactured goods currently in production. In semantic models, WIP is characterized by ProductionOrder individuals that have recorded OperationCompletion events for some but not all routing steps, with accumulated cost calculated from completed operations.

*Document prepared by William, Kent, Washington, United States  |  June 18, 2026  |  Pacific Daylight Time  |  Version 1.0  |  For internal use — manufacturing data architecture reference*
