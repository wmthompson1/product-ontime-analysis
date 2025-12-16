"""
Contextual UI Hints System for Manufacturing Domain Queries
Provides intelligent suggestions for complex data queries with domain-specific terminology
Enhanced with database-backed metadata from schema_edges table
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from app.ARANGO_hints_loader import get_ARANGO_hints_loader

class HintType(Enum):
    ACRONYM = "acronym"
    FIELD_SUGGESTION = "field_suggestion"
    QUERY_COMPLETION = "query_completion"
    BUSINESS_CONTEXT = "business_context"
    TABLE_RELATIONSHIP = "table_relationship"

@dataclass
class ContextualHint:
    """Structured hint with context and confidence"""
    text: str
    hint_type: HintType
    confidence: float
    explanation: str
    suggested_fields: List[str] = None
    example_query: str = None

class ManufacturingDomainHints:
    """Manufacturing-specific contextual hints and terminology"""
    
    def __init__(self):
        # Manufacturing acronyms and their meanings
        self.acronym_mappings = {
            'NCM': {
                'full_name': 'Non-Conformant Material',
                'related_fields': ['defect_rate', 'quality_status', 'conformance_flag', 'ncm_count'],
                'related_tables': ['product_defects', 'quality_control', 'inspection_results'],
                'context': 'quality control and defect tracking'
            },
            'OTD': {
                'full_name': 'On-Time Delivery',
                'related_fields': ['ontime_rate', 'delivery_date', 'target_date', 'delivery_performance'],
                'related_tables': ['daily_deliveries', 'suppliers', 'shipments'],
                'context': 'supply chain performance metrics'
            },
            'OEE': {
                'full_name': 'Overall Equipment Effectiveness',
                'related_fields': ['availability', 'performance', 'quality', 'oee_score'],
                'related_tables': ['production_metrics', 'equipment_status'],
                'context': 'manufacturing efficiency measurement'
            },
            'SPC': {
                'full_name': 'Statistical Process Control',
                'related_fields': ['control_limits', 'process_capability', 'variation'],
                'related_tables': ['process_control', 'measurements'],
                'context': 'process monitoring and control'
            },
            'DPMO': {
                'full_name': 'Defects Per Million Opportunities',
                'related_fields': ['defect_count', 'opportunity_count', 'dpmo_rate'],
                'related_tables': ['quality_metrics', 'production_data'],
                'context': 'quality measurement in Six Sigma'
            },
            'MTBF': {
                'full_name': 'Mean Time Between Failures',
                'related_fields': ['failure_date', 'repair_date', 'uptime', 'downtime'],
                'related_tables': ['equipment_failures', 'maintenance_records'],
                'context': 'reliability and maintenance planning'
            },
            'CAPA': {
                'full_name': 'Corrective and Preventive Action',
                'related_fields': ['action_type', 'completion_date', 'effectiveness'],
                'related_tables': ['corrective_actions', 'audit_findings'],
                'context': 'quality management and compliance'
            }
        }
        
        # Business context mappings
        self.business_contexts = {
            'quality': {
                'keywords': ['defect', 'quality', 'conformance', 'inspection', 'reject'],
                'suggested_metrics': ['defect_rate', 'quality_score', 'pass_rate', 'ncm_count'],
                'common_queries': [
                    'Show products with defect rates above threshold',
                    'Find quality trends by production line',
                    'Compare defect rates between shifts'
                ]
            },
            'supply_chain': {
                'keywords': ['supplier', 'delivery', 'shipment', 'vendor', 'procurement'],
                'suggested_metrics': ['ontime_rate', 'delivery_performance', 'lead_time'],
                'common_queries': [
                    'Find suppliers with poor delivery performance',
                    'Show delivery trends by region',
                    'Compare supplier performance metrics'
                ]
            },
            'production': {
                'keywords': ['production', 'manufacturing', 'output', 'efficiency', 'throughput'],
                'suggested_metrics': ['production_volume', 'efficiency_rate', 'cycle_time'],
                'common_queries': [
                    'Show production efficiency by line',
                    'Find bottlenecks in manufacturing process',
                    'Compare output across shifts'
                ]
            },
            'financial': {
                'keywords': ['cost', 'profit', 'margin', 'revenue', 'budget'],
                'suggested_metrics': ['profit_margin', 'cost_per_unit', 'revenue'],
                'common_queries': [
                    'Show profit margins by product line',
                    'Find cost drivers in production',
                    'Compare financial performance across quarters'
                ]
            }
        }
        
        # Field name patterns and their business meanings
        self.field_patterns = {
            r'.*_rate$': 'Performance or percentage metric',
            r'.*_count$': 'Counting metric or quantity',
            r'.*_date$': 'Timestamp or date field',
            r'.*_id$': 'Identifier or foreign key',
            r'.*_score$': 'Calculated performance metric',
            r'.*_margin$': 'Financial margin or profit metric',
            r'.*_volume$': 'Quantity or production volume',
            r'.*_cost$': 'Cost or expense metric'
        }
        
        # Query completion suggestions
        self.query_starters = {
            'quality_analysis': [
                "Show me products with NCM rates above",
                "Find quality trends for",
                "Compare defect rates between",
                "Which production lines have the highest"
            ],
            'supplier_performance': [
                "Show suppliers with OTD below",
                "Find delivery performance for",
                "Compare supplier metrics across",
                "Which vendors are underperforming on"
            ],
            'production_efficiency': [
                "Show OEE metrics for",
                "Find production bottlenecks in",
                "Compare efficiency across",
                "Which equipment has the lowest"
            ]
        }

class ContextualHintEngine:
    """Main engine for generating contextual hints with database integration"""
    
    def __init__(self, use_database: bool = True):
        self.domain_hints = ManufacturingDomainHints()
        self.recent_queries = []  # Track recent queries for context
        self.use_database = use_database
        self.db_loader = None
        
        # Initialize database loader if enabled
        if self.use_database:
            try:
                self.db_loader = get_ARANGO_hints_loader()
            except Exception as e:
                print(f"Warning: Could not initialize database hints loader: {e}")
                self.use_database = False
    
    def generate_hints(self, partial_query: str, available_fields: List[str] = None, table_name: str = None) -> List[ContextualHint]:
        """Generate contextual hints based on partial query input"""
        hints = []
        
        # Clean and analyze the partial query
        query_lower = partial_query.lower().strip()
        
        # Extract table name from query if present (e.g., "Quality Control | Example: ...")
        if not table_name and '|' in partial_query:
            parts = partial_query.split('|')
            if len(parts) >= 2:
                table_name = parts[0].strip()
        
        # 1. Try database-backed hints first (production-ready)
        if self.use_database and self.db_loader:
            try:
                db_hints = self._get_ARANGO_hints(partial_query, table_name)
                hints.extend(db_hints)
            except Exception as e:
                print(f"Error loading database hints: {e}")
        
        # 2. Detect acronyms and provide expansions
        acronym_hints = self._detect_acronyms(partial_query)
        hints.extend(acronym_hints)
        
        # 3. Suggest relevant fields based on context
        if available_fields:
            field_hints = self._suggest_fields(query_lower, available_fields)
            hints.extend(field_hints)
        
        # 4. Provide query completion suggestions
        completion_hints = self._suggest_completions(query_lower)
        hints.extend(completion_hints)
        
        # 5. Add business context hints
        context_hints = self._add_business_context(query_lower)
        hints.extend(context_hints)
        
        # Sort by confidence and return top suggestions
        hints.sort(key=lambda x: x.confidence, reverse=True)
        return hints[:8]  # Return top 8 hints
    
    def _get_ARANGO_hints(self, query: str, table_name: str = None) -> List[ContextualHint]:
        """Get hints from database-backed schema metadata"""
        hints = []
        
        if not self.db_loader:
            return hints
        
        # Convert table name to database format (e.g., "Quality Control" → "quality_control")
        if table_name:
            db_table_name = table_name.lower().replace(' ', '_')
            
            # Get edges for this table
            edges = self.db_loader.get_edges_for_node(db_table_name)
            
            for edge in edges:
                if edge.get('context') or edge.get('join_column_description'):
                    hint = ContextualHint(
                        text=f"{edge['from_table']} → {edge['to_table']}: {edge.get('natural_language_alias', edge['relationship_type'])}",
                        hint_type=HintType.TABLE_RELATIONSHIP,
                        confidence=0.95,
                        explanation=edge.get('join_column_description', edge.get('context', '')),
                        suggested_fields=[edge['join_column']] if edge.get('join_column') else [],
                        example_query=edge.get('few_shot_example')
                    )
                    hints.append(hint)
        
        # Get acronym hints from database
        db_acronyms = self.db_loader.build_acronym_mappings()
        for acronym, data in db_acronyms.items():
            if acronym in query.upper():
                hint = ContextualHint(
                    text=f"{acronym} = {data['full_name']} (from database)",
                    hint_type=HintType.ACRONYM,
                    confidence=0.98,  # Higher confidence for database-backed hints
                    explanation=data.get('context', f"Relates to {', '.join(data['related_tables'][:3])}"),
                    suggested_fields=data.get('related_fields', [])[:5],
                    example_query=data.get('example_sql')
                )
                hints.append(hint)
        
        return hints
    
    def _detect_acronyms(self, query: str) -> List[ContextualHint]:
        """Detect and expand manufacturing acronyms"""
        hints = []
        
        # Find acronyms in the query
        acronym_pattern = r'\b([A-Z]{2,6})\b'
        found_acronyms = re.findall(acronym_pattern, query)
        
        for acronym in found_acronyms:
            if acronym in self.domain_hints.acronym_mappings:
                mapping = self.domain_hints.acronym_mappings[acronym]
                hint = ContextualHint(
                    text=f"{acronym} = {mapping['full_name']}",
                    hint_type=HintType.ACRONYM,
                    confidence=0.95,
                    explanation=f"Manufacturing term: {mapping['context']}",
                    suggested_fields=mapping['related_fields'],
                    example_query=f"Show {mapping['full_name']} metrics for last month"
                )
                hints.append(hint)
        
        # Also suggest acronyms that might be relevant
        for acronym, mapping in self.domain_hints.acronym_mappings.items():
            if any(keyword in query.lower() for keyword in mapping['context'].split()):
                if acronym not in found_acronyms:  # Don't duplicate
                    hint = ContextualHint(
                        text=f"Consider {acronym} ({mapping['full_name']})",
                        hint_type=HintType.ACRONYM,
                        confidence=0.75,
                        explanation=f"Related to {mapping['context']}",
                        suggested_fields=mapping['related_fields']
                    )
                    hints.append(hint)
        
        return hints
    
    def _suggest_fields(self, query: str, available_fields: List[str]) -> List[ContextualHint]:
        """Suggest relevant database fields based on query context"""
        hints = []
        
        # Score fields based on relevance to query
        field_scores = {}
        
        for field in available_fields:
            score = 0
            
            # Direct name matching
            if any(word in field.lower() for word in query.split()):
                score += 0.8
            
            # Pattern matching
            for pattern, description in self.domain_hints.field_patterns.items():
                if re.match(pattern, field):
                    score += 0.4
                    break
            
            # Context matching
            for context, data in self.domain_hints.business_contexts.items():
                if any(keyword in query for keyword in data['keywords']):
                    if field in data['suggested_metrics']:
                        score += 0.6
            
            if score > 0.3:
                field_scores[field] = score
        
        # Create hints for top-scoring fields
        sorted_fields = sorted(field_scores.items(), key=lambda x: x[1], reverse=True)
        for field, score in sorted_fields[:4]:
            # Get field description
            description = "Database field"
            for pattern, desc in self.domain_hints.field_patterns.items():
                if re.match(pattern, field):
                    description = desc
                    break
            
            hint = ContextualHint(
                text=f"Use field: {field}",
                hint_type=HintType.FIELD_SUGGESTION,
                confidence=min(score, 0.9),
                explanation=description,
                suggested_fields=[field]
            )
            hints.append(hint)
        
        return hints
    
    def _suggest_completions(self, query: str) -> List[ContextualHint]:
        """Suggest query completions based on common patterns"""
        hints = []
        
        # Determine query category
        category = None
        if any(word in query for word in ['quality', 'defect', 'ncm']):
            category = 'quality_analysis'
        elif any(word in query for word in ['supplier', 'delivery', 'otd']):
            category = 'supplier_performance'
        elif any(word in query for word in ['production', 'efficiency', 'oee']):
            category = 'production_efficiency'
        
        if category and category in self.domain_hints.query_starters:
            for starter in self.domain_hints.query_starters[category]:
                if len(query) < 20:  # Only suggest for short queries
                    hint = ContextualHint(
                        text=starter,
                        hint_type=HintType.QUERY_COMPLETION,
                        confidence=0.7,
                        explanation="Common query pattern in manufacturing",
                        example_query=starter + " [specific criteria]"
                    )
                    hints.append(hint)
        
        return hints
    
    def _add_business_context(self, query: str) -> List[ContextualHint]:
        """Add business context and explanations"""
        hints = []
        
        # Identify the business domain
        for context, data in self.domain_hints.business_contexts.items():
            if any(keyword in query for keyword in data['keywords']):
                hint = ContextualHint(
                    text=f"Business context: {context.replace('_', ' ').title()}",
                    hint_type=HintType.BUSINESS_CONTEXT,
                    confidence=0.8,
                    explanation=f"Suggested metrics: {', '.join(data['suggested_metrics'][:3])}",
                    suggested_fields=data['suggested_metrics']
                )
                hints.append(hint)
                break
        
        return hints
    
    def add_query_to_history(self, query: str, success: bool = True):
        """Track successful queries for learning"""
        self.recent_queries.append({
            'query': query,
            'timestamp': None,  # Would use datetime in production
            'success': success
        })
        
        # Keep only recent queries
        if len(self.recent_queries) > 50:
            self.recent_queries = self.recent_queries[-50:]

# Global hint engine instance
hint_engine = ContextualHintEngine()

def get_contextual_hints(partial_query: str, available_fields: List[str] = None, table_name: str = None) -> List[Dict]:
    """Main function to get contextual hints for UI with database integration"""
    hints = hint_engine.generate_hints(partial_query, available_fields, table_name)
    
    # Convert to dictionary format for JSON serialization
    return [
        {
            'text': hint.text,
            'type': hint.hint_type.value,
            'confidence': hint.confidence,
            'explanation': hint.explanation,
            'suggested_fields': hint.suggested_fields or [],
            'example_query': hint.example_query
        }
        for hint in hints
    ]

def expand_acronym(acronym: str) -> Optional[Dict]:
    """Get detailed information about a specific acronym"""
    acronym = acronym.upper()
    if acronym in hint_engine.domain_hints.acronym_mappings:
        mapping = hint_engine.domain_hints.acronym_mappings[acronym]
        return {
            'acronym': acronym,
            'full_name': mapping['full_name'],
            'context': mapping['context'],
            'related_fields': mapping['related_fields'],
            'related_tables': mapping['related_tables']
        }
    return None