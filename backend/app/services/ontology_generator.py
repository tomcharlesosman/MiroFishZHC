"""
Ontology generation service.
Endpoint 1: analyze text and generate entity and relationship types for social simulation.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


# Ontology-generation system prompt
ONTOLOGY_SYSTEM_PROMPT = """You are an expert knowledge-graph ontology designer. Your task is to analyze the provided source material and simulation requirement, then design entity types and relationship types for a **social media opinion simulation**.

Important: you must output valid JSON only and nothing else.

## Core context

We are building a **social media opinion simulation system**. In this system:
- each entity is a real-world actor or account that can speak, interact, and spread information on social platforms
- entities influence one another through replies, reposts, comments, and reactions
- we want to simulate how different actors respond to an event and how information spreads

Therefore, **entities must be real-world actors that can plausibly speak and interact on social media**.

Allowed entities include:
- specific people such as public figures, involved parties, opinion leaders, experts, and ordinary individuals
- companies and businesses, including their official accounts
- institutions and organizations such as universities, associations, NGOs, and unions
- government departments and regulators
- media organizations such as newspapers, broadcasters, websites, and self-media outlets
- social media platforms themselves
- representative groups such as alumni groups, fandoms, or activist communities

Disallowed entities include:
- abstract concepts such as "public opinion", "emotion", or "trend"
- themes or topics such as "academic integrity" or "education reform"
- viewpoints or stances such as "supporters" or "opponents"

## Output format

Return JSON in this structure:

```json
{
  "entity_types": [
    {
      "name": "EntityTypeName in PascalCase",
      "description": "Short English description under 100 characters",
      "attributes": [
        {
          "name": "attribute_name in snake_case",
          "type": "text",
          "description": "Attribute description in English"
        }
      ],
      "examples": ["Example entity 1", "Example entity 2"]
    }
  ],
  "edge_types": [
    {
      "name": "RELATION_TYPE in UPPER_SNAKE_CASE",
      "description": "Short English description under 100 characters",
      "source_targets": [
        {"source": "SourceEntityType", "target": "TargetEntityType"}
      ],
      "attributes": []
    }
  ],
  "analysis_summary": "Brief English summary of what the material contains"
}
```

## Design rules

### 1. Entity-type design

You must return exactly 10 entity types.

The final 2 types must be fallback types:
- `Person`: fallback for any natural person who does not fit a more specific type
- `Organization`: fallback for any institution or group that does not fit a more specific type

The other 8 types should be specific types derived from the material.

Examples:
- for an academic controversy: `Student`, `Professor`, `University`
- for a business event: `Company`, `CEO`, `Employee`

Why fallback types matter:
- the material may contain many loosely specified people such as "a teacher", "a passerby", or "a netizen"
- if no specific type fits, they should map to `Person`
- similarly, small or temporary institutions should map to `Organization`

Specific-type design principles:
- identify the most important or frequent actor types in the material
- each specific type should have a clear boundary and avoid overlap
- each description should explain how the type differs from the fallback type

### 2. Relationship-type design

- return 6 to 10 relationship types
- relationships should reflect realistic social, institutional, or media connections
- make sure source_targets cover the entity types you define

### 3. Attribute design

- give each entity type 1 to 3 important attributes
- do not use reserved names such as `name`, `uuid`, `group_id`, `created_at`, or `summary`
- prefer names like `full_name`, `title`, `role`, `position`, `location`, or `description`

## Reference examples

Specific people:
- Student
- Professor
- Journalist
- Celebrity
- Executive
- Official
- Lawyer
- Doctor

Fallback people:
- Person

Specific organizations:
- University
- Company
- GovernmentAgency
- MediaOutlet
- Hospital
- School
- NGO

Fallback organizations:
- Organization

Relationship ideas:
- WORKS_FOR
- STUDIES_AT
- AFFILIATED_WITH
- REPRESENTS
- REGULATES
- REPORTS_ON
- COMMENTS_ON
- RESPONDS_TO
- SUPPORTS
- OPPOSES
- COLLABORATES_WITH
- COMPETES_WITH
"""


class OntologyGenerator:
    """
    Ontology generator.
    Analyzes text and generates entity and relationship type definitions.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
    
    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an ontology definition.

        Args:
            document_texts: List of document texts
            simulation_requirement: Simulation requirement description
            additional_context: Additional context

        Returns:
            Ontology definition (`entity_types`, `edge_types`, etc.)
        """
        # Build the user message.
        user_message = self._build_user_message(
            document_texts, 
            simulation_requirement,
            additional_context
        )
        
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Call the LLM.
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        # Validate and post-process.
        result = self._validate_and_process(result)
        
        return result
    
    # Maximum text length sent to the LLM (50k characters).
    MAX_TEXT_LENGTH_FOR_LLM = 50000
    
    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Build the user message."""
        
        # Merge the text.
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)
        
        # Truncate if the text exceeds 50k characters; this only affects the LLM input, not graph construction.
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(original document length: {original_length} characters; only the first {self.MAX_TEXT_LENGTH_FOR_LLM} characters were sent for ontology analysis)..."
        
        message = f"""## Simulation requirement

{simulation_requirement}

## Source material

{combined_text}
"""
        
        if additional_context:
            message += f"""
## Additional context

{additional_context}
"""
        
        message += """
Design entity types and relationship types suitable for a social opinion simulation.

Rules you must follow:
1. Output exactly 10 entity types
2. The last 2 must be the fallback types Person and Organization
3. The first 8 must be specific types derived from the material
4. All entity types must be real-world actors that can speak or act, not abstract concepts
5. Do not use reserved attribute names like name, uuid, or group_id; use alternatives like full_name or org_name
"""
        
        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and post-process the result."""
        
        # Ensure required fields exist.
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""
        
        # Validate entity types.
        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # Ensure description stays within 100 characters.
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."
        
        # Validate relationship types.
        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."
        
        # Zep API limit: at most 10 custom entity types and 10 custom edge types.
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10
        
        # Fallback type definitions.
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }
        
        # Check whether fallback types already exist.
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names
        
        # Fallback types that still need to be added.
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)
        
        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)
            
            # If adding them would exceed the limit, remove some existing types.
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # Compute how many types must be removed.
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # Remove from the end to preserve the earlier, more specific types.
                result["entity_types"] = result["entity_types"][:-to_remove]
            
            # Add fallback types.
            result["entity_types"].extend(fallbacks_to_add)
        
        # Final guard to ensure the limit is not exceeded.
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]
        
        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]
        
        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Convert the ontology definition into Python code, similar to `ontology.py`.
        
        Args:
            ontology: Ontology definition
            
        Returns:
            Python code string
        """
        code_lines = [
            '"""',
            'Custom entity type definitions',
            'Automatically generated by JunoFish for social opinion simulation',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entity type definitions ==============',
            '',
        ]
        
        # Generate entity types.
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== Relationship type definitions ==============')
        code_lines.append('')
        
        # Generate relationship types.
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # Convert to a PascalCase class name.
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # Generate type dictionaries.
        code_lines.append('# ============== Type configuration ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # Generate the source_targets mapping for edges.
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)
