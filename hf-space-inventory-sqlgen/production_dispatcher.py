"""
ProductionDispatcher - Hybrid RAG Semantic Router
===================================================
Takes natural language questions and routes them through:
  1. LLM (HuggingFace Inference) → Closed-vocabulary intent/concept extraction
  2. SolderEngine → Governed SQL assembly from approved snippets

The LLM acts as a Semantic Router, NOT a SQL generator.
All SQL comes from SME-approved, human-governed ground truth.

Fallback: Mock resolver for demo/testing when API is unavailable.
"""

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from solder_engine import SolderEngine, SQLITE_DB_PATH

HF_DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

MOCK_ROUTES = {
    "cost": {
        "intent": "defect_cost_analysis",
        "concepts": ["DefectSeverityCost"],
        "perspective": "Finance"
    },
    "defect": {
        "intent": "defect_quality_trending",
        "concepts": ["DefectSeverityQuality"],
        "perspective": "Quality"
    },
    "customer": {
        "intent": "defect_customer_impact",
        "concepts": ["DefectSeverityCustomer"],
        "perspective": "Customer"
    },
    "supplier": {
        "intent": "supplier_scorecard",
        "concepts": ["DeliveryPerformanceSupplier"],
        "perspective": "Operations"
    },
    "oee": {
        "intent": "oee_operational",
        "concepts": ["OEEOperational"],
        "perspective": "Operations"
    },
    "maintenance": {
        "intent": "maintenance_scheduling",
        "concepts": ["EquipmentStateMaintenance"],
        "perspective": "Operations"
    },
    "schedule": {
        "intent": "schedule_adherence",
        "concepts": ["OrderLifecycleState"],
        "perspective": "Operations"
    },
    "ncm": {
        "intent": "defect_cost_analysis",
        "concepts": ["DefectSeverityCost", "NCMDispositionFinance"],
        "perspective": "Finance"
    },
    "quality": {
        "intent": "defect_quality_trending",
        "concepts": ["DefectSeverityQuality", "DefectSeverityCost"],
        "perspective": "Quality"
    },
    "penalty": {
        "intent": "supplier_cost_penalties",
        "concepts": ["DeliveryPerformanceFinance"],
        "perspective": "Finance"
    },
}


@dataclass
class DispatchResult:
    user_query: str
    intent: str
    concepts: List[str]
    perspective: str
    assembled_sql: str
    assembly_report: List[str]
    warnings: List[str]
    routing_mode: str
    routing_confidence: str = ""
    out_of_scope: bool = False


class ProductionDispatcher:

    def __init__(self, solder_engine: SolderEngine = None,
                 db_path: str = None, use_live_api: bool = True,
                 hf_model: str = None):
        self.solder = solder_engine or SolderEngine()
        self.db_path = db_path or SQLITE_DB_PATH
        self.use_live_api = use_live_api
        self.hf_model = hf_model or HF_DEFAULT_MODEL

        self.intents = self._load_vocabulary("SELECT intent_name FROM schema_intents")
        self.concepts = self._load_vocabulary("SELECT concept_name FROM schema_concepts")
        self.perspectives = self._load_vocabulary("SELECT perspective_name FROM schema_perspectives")

        self.intent_details = self._load_intent_details()
        self.intent_binding_map = self._load_intent_binding_map()

    def _load_vocabulary(self, query: str) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(query).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def _load_intent_details(self) -> List[Dict[str, str]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT intent_name, intent_category, description, typical_question,
                       primary_binding_key
                FROM schema_intents ORDER BY intent_category
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _load_intent_binding_map(self) -> Dict[str, str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute("""
                SELECT intent_name, primary_binding_key
                FROM schema_intents
                WHERE primary_binding_key IS NOT NULL
            """).fetchall()
            return {r[0]: r[1] for r in rows}
        finally:
            conn.close()

    def _build_system_prompt(self) -> str:
        intent_block = "\n".join(
            f"  - {d['intent_name']} ({d['intent_category']}): {d['description']}"
            for d in self.intent_details
        )
        concept_block = ", ".join(self.concepts)
        perspective_block = ", ".join(self.perspectives)

        return f"""You are a Semantic Router for a manufacturing intelligence system.
Your ONLY job is to map a user's natural language question to the correct
Intent, Concepts, and Perspective from a CLOSED vocabulary.

AVAILABLE INTENTS:
{intent_block}

AVAILABLE CONCEPTS: {concept_block}

AVAILABLE PERSPECTIVES: {perspective_block}

RULES:
1. You MUST return ONLY a JSON object. No explanation, no markdown, no extra text.
2. The "intent" field MUST be exactly one of the AVAILABLE INTENTS listed above.
3. The "concepts" field MUST be a list of 1-3 items from AVAILABLE CONCEPTS.
4. The "perspective" field MUST be exactly one of the AVAILABLE PERSPECTIVES.
5. If the question is unrelated to manufacturing, return:
   {{"intent": "OUT_OF_SCOPE", "concepts": [], "perspective": "", "confidence": "none"}}
6. Include a "confidence" field: "high", "medium", or "low".

RETURN FORMAT (JSON only, no other text):
{{"intent": "...", "concepts": ["...", "..."], "perspective": "...", "confidence": "..."}}"""

    def extract_via_llm(self, user_query: str) -> Dict[str, Any]:
        try:
            from huggingface_hub import InferenceClient

            hf_token = os.environ.get("HF_TOKEN")
            client = InferenceClient(
                provider="hf-inference",
                api_key=hf_token
            )

            response = client.chat.completions.create(
                model=self.hf_model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_tokens=200
            )

            content = response.choices[0].message.content

            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)

            if parsed.get("intent") not in self.intents and parsed.get("intent") != "OUT_OF_SCOPE":
                parsed["confidence"] = "low"
                parsed["warning"] = f"LLM returned unknown intent: {parsed.get('intent')}"

            filtered_concepts = [c for c in parsed.get("concepts", []) if c in self.concepts]
            if len(filtered_concepts) < len(parsed.get("concepts", [])):
                parsed["warning"] = parsed.get("warning", "") + " Some concepts filtered (not in vocabulary)."
            parsed["concepts"] = filtered_concepts

            return parsed

        except json.JSONDecodeError as e:
            return {
                "intent": "ERROR",
                "concepts": [],
                "perspective": "",
                "confidence": "none",
                "error": f"Failed to parse LLM JSON response: {e}"
            }
        except Exception as e:
            return {
                "intent": "ERROR",
                "concepts": [],
                "perspective": "",
                "confidence": "none",
                "error": str(e)
            }

    def extract_via_mock(self, user_query: str) -> Dict[str, Any]:
        query_lower = user_query.lower()

        for keyword, route in MOCK_ROUTES.items():
            if keyword in query_lower:
                return {
                    "intent": route["intent"],
                    "concepts": route["concepts"],
                    "perspective": route["perspective"],
                    "confidence": "mock"
                }

        return {
            "intent": "OUT_OF_SCOPE",
            "concepts": [],
            "perspective": "",
            "confidence": "mock"
        }

    def dispatch(self, user_query: str,
                 perspective_override: str = None,
                 force_mock: bool = False,
                 base_table: str = "stg_manufacturing_flat",
                 target_dialect: str = "sqlite") -> DispatchResult:

        if force_mock or not self.use_live_api:
            semantic_map = self.extract_via_mock(user_query)
            routing_mode = "mock"
        else:
            semantic_map = self.extract_via_llm(user_query)
            if semantic_map.get("intent") == "ERROR":
                semantic_map = self.extract_via_mock(user_query)
                routing_mode = "mock (API fallback)"
            else:
                routing_mode = f"live (HF: {self.hf_model})"

        intent = semantic_map.get("intent", "OUT_OF_SCOPE")
        concepts = semantic_map.get("concepts", [])
        perspective = perspective_override or semantic_map.get("perspective", "")
        confidence = semantic_map.get("confidence", "")

        if intent == "OUT_OF_SCOPE":
            return DispatchResult(
                user_query=user_query,
                intent="OUT_OF_SCOPE",
                concepts=[],
                perspective="",
                assembled_sql="-- Question is outside manufacturing domain scope",
                assembly_report=["Question could not be mapped to any manufacturing intent."],
                warnings=["OUT_OF_SCOPE: Try asking about defects, costs, suppliers, OEE, or scheduling."],
                routing_mode=routing_mode,
                routing_confidence=confidence,
                out_of_scope=True
            )

        binding_key = self.intent_binding_map.get(intent)
        if binding_key:
            binding_result = self.solder.resolve_by_binding_key(binding_key, target_dialect=target_dialect)
            if binding_result.get("sql"):
                report = [f"Resolved via primary_binding_key: `{binding_key}`"]
                report.extend(binding_result.get("report", []))
                warnings = binding_result.get("warnings", [])
                if semantic_map.get("warning"):
                    warnings.insert(0, semantic_map["warning"])
                return DispatchResult(
                    user_query=user_query,
                    intent=intent,
                    concepts=concepts,
                    perspective=perspective,
                    assembled_sql=binding_result["sql"],
                    assembly_report=report,
                    warnings=warnings,
                    routing_mode=routing_mode,
                    routing_confidence=confidence
                )

        if not concepts:
            return DispatchResult(
                user_query=user_query,
                intent=intent,
                concepts=[],
                perspective=perspective,
                assembled_sql=f"-- No concepts identified for intent '{intent}'",
                assembly_report=[f"Intent '{intent}' identified but no concepts extracted."],
                warnings=["No concepts found. Try being more specific about what data you need."],
                routing_mode=routing_mode,
                routing_confidence=confidence
            )

        assembly_result = self.solder.assemble_query(
            intent=intent,
            perspective=perspective,
            concepts=concepts,
            base_table=base_table,
            target_dialect=target_dialect
        )

        warnings = assembly_result.get("warnings", [])
        if semantic_map.get("warning"):
            warnings.insert(0, semantic_map["warning"])

        return DispatchResult(
            user_query=user_query,
            intent=intent,
            concepts=concepts,
            perspective=perspective,
            assembled_sql=assembly_result.get("sql", ""),
            assembly_report=assembly_result.get("report", []),
            warnings=warnings,
            routing_mode=routing_mode,
            routing_confidence=confidence
        )
