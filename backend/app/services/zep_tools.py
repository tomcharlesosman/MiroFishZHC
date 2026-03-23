"""
Zep retrieval tools.
Wrap graph search, node inspection, and edge lookup helpers for the Report Agent.

Core retrieval tools:
1. InsightForge - strongest hybrid retrieval, with sub-question generation and multi-angle analysis.
2. PanoramaSearch - broad retrieval for a full view, including expired content.
3. QuickSearch - lightweight direct lookup.
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges

logger = get_logger('mirofish.zep_tools')


@dataclass
class SearchResult:
    """Search results."""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count
        }
    
    def to_text(self) -> str:
        """Convert the result to LLM-friendly text."""
        text_parts = [f"Search query: {self.query}", f"Found {self.total_count} relevant items"]
        
        if self.facts:
            text_parts.append("\n### Relevant facts:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Node details."""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes
        }
    
    def to_text(self) -> str:
        """Convert the result to text."""
        entity_type = next((l for l in self.labels if l not in ["Entity", "Node"]), "Unknown type")
        return f"Entity: {self.name} (Type: {entity_type})\nSummary: {self.summary}"


@dataclass
class EdgeInfo:
    """Edge details."""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    # Temporal metadata
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at
        }
    
    def to_text(self, include_temporal: bool = False) -> str:
        """Convert the edge to text."""
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"Relation: {source} --[{self.name}]--> {target}\nFact: {self.fact}"
        
        if include_temporal:
            valid_at = self.valid_at or "Unknown"
            invalid_at = self.invalid_at or "Present"
            base_text += f"\nValidity: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (Expired: {self.expired_at})"
        
        return base_text
    
    @property
    def is_expired(self) -> bool:
        """Whether the edge has expired."""
        return self.expired_at is not None
    
    @property
    def is_invalid(self) -> bool:
        """Whether the edge has become invalid."""
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """
    Deep Insight retrieval result (InsightForge).
    Includes retrieval results for multiple sub-questions and a combined analysis.
    """
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    
    # Results across multiple retrieval dimensions
    semantic_facts: List[str] = field(default_factory=list)  # Semantic search results
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)  # Entity insights
    relationship_chains: List[str] = field(default_factory=list)  # Relationship chains

    # Aggregate statistics
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships
        }
    
    def to_text(self) -> str:
        """Convert the result to detailed text for the LLM."""
        text_parts = [
            "## Deep Forecast Analysis",
            f"Analysis query: {self.query}",
            f"Scenario: {self.simulation_requirement}",
            "\n### Forecast statistics",
            f"- Relevant prediction facts: {self.total_facts}",
            f"- Entities involved: {self.total_entities}",
            f"- Relationship chains: {self.total_relationships}"
        ]
        
        if self.sub_queries:
            text_parts.append("\n### Analytical sub-questions")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")
        
        if self.semantic_facts:
            text_parts.append("\n### Key facts (quote these original lines in the report)")
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        if self.entity_insights:
            text_parts.append("\n### Core entities")
            for entity in self.entity_insights:
                text_parts.append(f"- **{entity.get('name', 'Unknown')}** ({entity.get('type', 'Entity')})")
                if entity.get('summary'):
                    text_parts.append(f"  Summary: \"{entity.get('summary')}\"")
                if entity.get('related_facts'):
                    text_parts.append(f"  Related facts: {len(entity.get('related_facts', []))}")
        
        if self.relationship_chains:
            text_parts.append("\n### Relationship chains")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """
    Panorama search result.
    Includes all relevant information, including expired content.
    """
    query: str
    
    # All nodes
    all_nodes: List[NodeInfo] = field(default_factory=list)
    # All edges, including expired ones
    all_edges: List[EdgeInfo] = field(default_factory=list)
    # Currently valid facts
    active_facts: List[str] = field(default_factory=list)
    # Expired or invalid facts (historical record)
    historical_facts: List[str] = field(default_factory=list)

    # Statistics
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count
        }
    
    def to_text(self) -> str:
        """Convert the result to text without truncation."""
        text_parts = [
            "## Panorama Search Results",
            f"Query: {self.query}",
            "\n### Statistics",
            f"- Total nodes: {self.total_nodes}",
            f"- Total edges: {self.total_edges}",
            f"- Active facts: {self.active_count}",
            f"- Historical/expired facts: {self.historical_count}"
        ]
        
        if self.active_facts:
            text_parts.append("\n### Active facts (simulation output)")
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        if self.historical_facts:
            text_parts.append("\n### Historical/expired facts (change over time)")
            for i, fact in enumerate(self.historical_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        if self.all_nodes:
            text_parts.append("\n### Entities involved")
            for node in self.all_nodes:
                entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entity")
                text_parts.append(f"- **{node.name}** ({entity_type})")
        
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Interview result for a single agent."""
    agent_name: str
    agent_role: str  # Role type, such as student, teacher, or media
    agent_bio: str  # Short bio
    question: str  # Interview question
    response: str  # Interview answer
    key_quotes: List[str] = field(default_factory=list)  # Key quotes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes
        }
    
    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        text += f"_Profile summary: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Key quotes:**\n"
            for quote in self.key_quotes:
                # Normalize several quote styles.
                clean_quote = quote.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                clean_quote = clean_quote.replace('\u300c', '').replace('\u300d', '')
                clean_quote = clean_quote.strip()
                # Remove leading punctuation.
                while clean_quote and clean_quote[0] in '\uFF0C,;\uFF1B:\uFF1A\u3001\u3002\uFF01\uFF1F\n\r\t ':
                    clean_quote = clean_quote[1:]
                # Filter junk that just repeats numbered question labels.
                skip = False
                for d in '123456789':
                    if f'\u95ee\u9898{d}' in clean_quote:
                        skip = True
                        break
                if skip:
                    continue
                # Trim overlong excerpts at sentence boundaries where possible.
                if len(clean_quote) > 150:
                    dot_pos = clean_quote.find('\u3002', 80)
                    if dot_pos > 0:
                        clean_quote = clean_quote[:dot_pos + 1]
                    else:
                        clean_quote = clean_quote[:147] + "..."
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """
    Interview result.
    Includes interview answers from multiple simulated agents.
    """
    interview_topic: str  # Interview topic
    interview_questions: List[str]  # Interview question list

    # Selected agents
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    # Interview answers from each agent
    interviews: List[AgentInterview] = field(default_factory=list)

    # Why these agents were selected
    selection_reasoning: str = ""
    # Consolidated summary
    summary: str = ""

    # Statistics
    total_agents: int = 0
    interviewed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count
        }
    
    def to_text(self) -> str:
        """Convert the result to detailed text for the LLM and reports."""
        text_parts = [
            "## Deep Interview Report",
            f"**Interview topic:** {self.interview_topic}",
            f"**Interview count:** {self.interviewed_count} / {self.total_agents} simulated agents",
            "\n### Why these participants were selected",
            self.selection_reasoning or "(automatically selected)",
            "\n---",
            "\n### Interview transcript",
        ]

        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n#### Interview #{i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("(no interview records)\n\n---")

        text_parts.append("\n### Interview summary and core viewpoints")
        text_parts.append(self.summary or "(no summary)")

        return "\n".join(text_parts)


class ZepToolsService:
    """
    Zep retrieval tools.

    Core tools:
    1. insight_forge - deep retrieval with sub-question generation and multi-angle search
    2. panorama_search - broad retrieval for a full-picture view, including expired content
    3. quick_search - lightweight direct retrieval
    4. interview_agents - deep interviews with simulated agents for multi-perspective reporting

    Basic tools:
    - search_graph - semantic graph search
    - get_all_nodes - fetch all graph nodes
    - get_all_edges - fetch all graph edges, including temporal metadata
    - get_node_detail - fetch node details
    - get_node_edges - fetch edges related to a node
    - get_entities_by_type - fetch entities by type
    - get_entity_summary - fetch a summary of an entity's relationships
    """

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, api_key: Optional[str] = None, llm_client: Optional[LLMClient] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError("ZEP_API_KEY is not configured")

        self.client = Zep(api_key=self.api_key)
        # LLM client used by InsightForge for sub-question generation
        self._llm_client = llm_client
        logger.info("ZepToolsService initialized")
    
    @property
    def llm(self) -> LLMClient:
        """Initialize the LLM client lazily."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    def _call_with_retry(self, func, operation_name: str, max_retries: int = None):
        """Call an API function with retries."""
        max_retries = max_retries or self.MAX_RETRIES
        last_exception = None
        delay = self.RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Zep {operation_name} attempt {attempt + 1} failed: {str(e)[:100]}, "
                        f"retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Zep {operation_name} still failed after {max_retries} attempts: {str(e)}")
        
        raise last_exception
    
    def search_graph(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Semantic graph search.

        Uses hybrid search (semantic + BM25) to find relevant information in the graph.
        Falls back to local keyword matching if the Zep Cloud search API is unavailable.

        Args:
            graph_id: Graph ID (standalone graph)
            query: Search query
            limit: Number of results to return
            scope: Search scope, either "edges" or "nodes"

        Returns:
            SearchResult: Search results
        """
        logger.info(f"Graph search: graph_id={graph_id}, query={query[:50]}...")

        # Try the Zep Cloud Search API first.
        try:
            search_results = self._call_with_retry(
                func=lambda: self.client.graph.search(
                    graph_id=graph_id,
                    query=query,
                    limit=limit,
                    scope=scope,
                    reranker="cross_encoder"
                ),
                operation_name=f"graph_search(graph={graph_id})"
            )
            
            facts = []
            edges = []
            nodes = []
            
            # Parse edge search results.
            if hasattr(search_results, 'edges') and search_results.edges:
                for edge in search_results.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.append(edge.fact)
                    edges.append({
                        "uuid": getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', ''),
                        "name": getattr(edge, 'name', ''),
                        "fact": getattr(edge, 'fact', ''),
                        "source_node_uuid": getattr(edge, 'source_node_uuid', ''),
                        "target_node_uuid": getattr(edge, 'target_node_uuid', ''),
                    })
            
            # Parse node search results.
            if hasattr(search_results, 'nodes') and search_results.nodes:
                for node in search_results.nodes:
                    nodes.append({
                        "uuid": getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                        "name": getattr(node, 'name', ''),
                        "labels": getattr(node, 'labels', []),
                        "summary": getattr(node, 'summary', ''),
                    })
                    # Node summaries also count as facts.
                    if hasattr(node, 'summary') and node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Search complete: found {len(facts)} relevant facts")
            
            return SearchResult(
                facts=facts,
                edges=edges,
                nodes=nodes,
                query=query,
                total_count=len(facts)
            )
            
        except Exception as e:
            logger.warning(f"Zep Search API failed, falling back to local search: {str(e)}")
            # Fallback to local keyword matching.
            return self._local_search(graph_id, query, limit, scope)
    
    def _local_search(
        self, 
        graph_id: str, 
        query: str, 
        limit: int = 10,
        scope: str = "edges"
    ) -> SearchResult:
        """
        Local keyword matching fallback for the Zep Search API.

        Fetches all edges or nodes, then performs local keyword matching.

        Args:
            graph_id: Graph ID
            query: Search query
            limit: Number of results to return
            scope: Search scope

        Returns:
            SearchResult: Search results
        """
        logger.info(f"Using local search: query={query[:30]}...")
        
        facts = []
        edges_result = []
        nodes_result = []
        
        # Extract query keywords with a simple split strategy.
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def match_score(text: str) -> int:
            """Compute a simple query-to-text match score."""
            if not text:
                return 0
            text_lower = text.lower()
            # Full query match.
            if query_lower in text_lower:
                return 100
            # Keyword matches.
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score
        
        try:
            if scope in ["edges", "both"]:
                # Fetch all edges and score them.
                all_edges = self.get_all_edges(graph_id)
                scored_edges = []
                for edge in all_edges:
                    score = match_score(edge.fact) + match_score(edge.name)
                    if score > 0:
                        scored_edges.append((score, edge))
                
                # Sort by descending relevance score.
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                
                for score, edge in scored_edges[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append({
                        "uuid": edge.uuid,
                        "name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                        "target_node_uuid": edge.target_node_uuid,
                    })
            
            if scope in ["nodes", "both"]:
                # Fetch all nodes and score them.
                all_nodes = self.get_all_nodes(graph_id)
                scored_nodes = []
                for node in all_nodes:
                    score = match_score(node.name) + match_score(node.summary)
                    if score > 0:
                        scored_nodes.append((score, node))
                
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                
                for score, node in scored_nodes[:limit]:
                    nodes_result.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "labels": node.labels,
                        "summary": node.summary,
                    })
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")
            
            logger.info(f"Local search complete: found {len(facts)} relevant facts")

        except Exception as e:
            logger.error(f"Local search failed: {str(e)}")
        
        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts)
        )
    
    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """
        Fetch all nodes in the graph with pagination.

        Args:
            graph_id: Graph ID

        Returns:
            List of nodes
        """
        logger.info(f"Fetching all nodes for graph {graph_id}...")

        nodes = fetch_all_nodes(self.client, graph_id)

        result = []
        for node in nodes:
            node_uuid = getattr(node, 'uuid_', None) or getattr(node, 'uuid', None) or ""
            result.append(NodeInfo(
                uuid=str(node_uuid) if node_uuid else "",
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            ))

        logger.info(f"Fetched {len(result)} nodes")
        return result

    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[EdgeInfo]:
        """
        Fetch all edges in the graph with pagination and optional temporal metadata.

        Args:
            graph_id: Graph ID
            include_temporal: Whether to include temporal metadata

        Returns:
            List of edges with created_at, valid_at, invalid_at, and expired_at
        """
        logger.info(f"Fetching all edges for graph {graph_id}...")

        edges = fetch_all_edges(self.client, graph_id)

        result = []
        for edge in edges:
            edge_uuid = getattr(edge, 'uuid_', None) or getattr(edge, 'uuid', None) or ""
            edge_info = EdgeInfo(
                uuid=str(edge_uuid) if edge_uuid else "",
                name=edge.name or "",
                fact=edge.fact or "",
                source_node_uuid=edge.source_node_uuid or "",
                target_node_uuid=edge.target_node_uuid or ""
            )

            # Attach temporal metadata.
            if include_temporal:
                edge_info.created_at = getattr(edge, 'created_at', None)
                edge_info.valid_at = getattr(edge, 'valid_at', None)
                edge_info.invalid_at = getattr(edge, 'invalid_at', None)
                edge_info.expired_at = getattr(edge, 'expired_at', None)

            result.append(edge_info)

        logger.info(f"Fetched {len(result)} edges")
        return result
    
    def get_node_detail(self, node_uuid: str) -> Optional[NodeInfo]:
        """
        Fetch details for a single node.

        Args:
            node_uuid: Node UUID

        Returns:
            Node details or None
        """
        logger.info(f"Fetching node details: {node_uuid[:8]}...")
        
        try:
            node = self._call_with_retry(
                func=lambda: self.client.graph.node.get(uuid_=node_uuid),
                operation_name=f"get_node_detail(uuid={node_uuid[:8]}...)"
            )
            
            if not node:
                return None
            
            return NodeInfo(
                uuid=getattr(node, 'uuid_', None) or getattr(node, 'uuid', ''),
                name=node.name or "",
                labels=node.labels or [],
                summary=node.summary or "",
                attributes=node.attributes or {}
            )
        except Exception as e:
            logger.error(f"Failed to fetch node details: {str(e)}")
            return None
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """
        Fetch all edges related to a node.

        This works by fetching all graph edges and then filtering the edges
        whose source or target matches the specified node.

        Args:
            graph_id: Graph ID
            node_uuid: Node UUID

        Returns:
            List of related edges
        """
        logger.info(f"Fetching edges related to node {node_uuid[:8]}...")
        
        try:
            # Fetch all graph edges, then filter locally.
            all_edges = self.get_all_edges(graph_id)
            
            result = []
            for edge in all_edges:
                # Keep edges where the node is either source or target.
                if edge.source_node_uuid == node_uuid or edge.target_node_uuid == node_uuid:
                    result.append(edge)
            
            logger.info(f"Found {len(result)} edges related to the node")
            return result
            
        except Exception as e:
            logger.warning(f"Failed to fetch node edges: {str(e)}")
            return []
    
    def get_entities_by_type(
        self, 
        graph_id: str, 
        entity_type: str
    ) -> List[NodeInfo]:
        """
        Fetch entities by type.
        
        Args:
            graph_id: Graph ID
            entity_type: Entity type, for example Student or PublicFigure

        Returns:
            Matching entities
        """
        logger.info(f"Fetching entities of type {entity_type}...")
        
        all_nodes = self.get_all_nodes(graph_id)
        
        filtered = []
        for node in all_nodes:
            # Keep nodes whose labels include the requested type.
            if entity_type in node.labels:
                filtered.append(node)
        
        logger.info(f"Found {len(filtered)} entities of type {entity_type}")
        return filtered
    
    def get_entity_summary(
        self, 
        graph_id: str, 
        entity_name: str
    ) -> Dict[str, Any]:
        """
        Fetch a relationship summary for a specific entity.

        Searches for information related to the entity and returns a compact summary.

        Args:
            graph_id: Graph ID
            entity_name: Entity name

        Returns:
            Entity summary
        """
        logger.info(f"Fetching relationship summary for entity {entity_name}...")
        
        # Search for information related to the entity first.
        search_result = self.search_graph(
            graph_id=graph_id,
            query=entity_name,
            limit=20
        )
        
        # Try to find the entity in the node list.
        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break
        
        related_edges = []
        if entity_node:
            # Fetch the entity's related edges using the graph ID.
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)
        
        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges)
        }
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """
        Fetch graph statistics.

        Args:
            graph_id: Graph ID

        Returns:
            Graph statistics
        """
        logger.info(f"Fetching statistics for graph {graph_id}...")
        
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        
        # Count entity types.
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1
        
        # Count relation types.
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def get_simulation_context(
        self, 
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch context relevant to a simulation scenario.

        Performs a combined search for information related to the simulation requirement.

        Args:
            graph_id: Graph ID
            simulation_requirement: Simulation requirement description
            limit: Max items to keep per category

        Returns:
            Simulation context information
        """
        logger.info(f"Fetching simulation context: {simulation_requirement[:50]}...")
        
        # Search for information related to the simulation requirement.
        search_result = self.search_graph(
            graph_id=graph_id,
            query=simulation_requirement,
            limit=limit
        )
        
        # Fetch graph statistics.
        stats = self.get_graph_statistics(graph_id)
        
        # Fetch all entity nodes.
        all_nodes = self.get_all_nodes(graph_id)
        
        # Keep only entities with a concrete type, excluding bare Entity nodes.
        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary
                })
        
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],  # Limit the result size
            "total_entities": len(entities)
        }

    # ========== Core retrieval tools ==========
    
    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5
    ) -> InsightForgeResult:
        """
        InsightForge deep retrieval.

        Strong hybrid retrieval flow that automatically breaks the question down
        and searches across multiple angles:
        1. Use the LLM to break the question into sub-questions
        2. Run semantic search for each sub-question
        3. Extract related entities and load their details
        4. Trace relationship chains
        5. Combine everything into a deeper analytical view

        Args:
            graph_id: Graph ID
            query: User question
            simulation_requirement: Simulation requirement description
            report_context: Optional report context for better sub-question generation
            max_sub_queries: Maximum number of sub-questions
            
        Returns:
            InsightForgeResult: Deep retrieval result
        """
        logger.info(f"InsightForge deep retrieval: {query[:50]}...")
        
        result = InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=[]
        )
        
        # Step 1: Generate sub-questions with the LLM.
        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries
        )
        result.sub_queries = sub_queries
        logger.info(f"Generated {len(sub_queries)} sub-questions")
        
        # Step 2: Run semantic search for each sub-question.
        all_facts = []
        all_edges = []
        seen_facts = set()
        
        for sub_query in sub_queries:
            search_result = self.search_graph(
                graph_id=graph_id,
                query=sub_query,
                limit=15,
                scope="edges"
            )
            
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            
            all_edges.extend(search_result.edges)
        
        # Also search against the original question.
        main_search = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=20,
            scope="edges"
        )
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)
        
        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)
        
        # Step 3: Extract related entity UUIDs from edges and fetch only those entities.
        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                if source_uuid:
                    entity_uuids.add(source_uuid)
                if target_uuid:
                    entity_uuids.add(target_uuid)
        
        # Fetch all related entity details without truncation.
        entity_insights = []
        node_map = {}  # Used later to build relationship chains.

        for uuid in list(entity_uuids):  # Process all entities without truncation.
            if not uuid:
                continue
            try:
                # Fetch each related node individually.
                node = self.get_node_detail(uuid)
                if node:
                    node_map[uuid] = node
                    entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "Entity")

                    # Collect all facts related to this entity.
                    related_facts = [
                        f for f in all_facts 
                        if node.name.lower() in f.lower()
                    ]
                    
                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts  # Keep the full list.
                    })
            except Exception as e:
                logger.debug(f"Failed to fetch node {uuid}: {e}")
                continue
        
        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)
        
        # Step 4: Build all relationship chains without truncation.
        relationship_chains = []
        for edge_data in all_edges:  # Process all edges without truncation.
            if isinstance(edge_data, dict):
                source_uuid = edge_data.get('source_node_uuid', '')
                target_uuid = edge_data.get('target_node_uuid', '')
                relation_name = edge_data.get('name', '')
                
                source_name = node_map.get(source_uuid, NodeInfo('', '', [], '', {})).name or source_uuid[:8]
                target_name = node_map.get(target_uuid, NodeInfo('', '', [], '', {})).name or target_uuid[:8]
                
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)
        
        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)
        
        logger.info(
            f"InsightForge complete: {result.total_facts} facts, "
            f"{result.total_entities} entities, {result.total_relationships} relationships"
        )
        return result
    
    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5
    ) -> List[str]:
        """
        Generate sub-questions with the LLM.

        Break a complex question into multiple sub-questions that can be searched independently.
        """
        system_prompt = """You are an expert question analyst. Break a complex question into
multiple sub-questions that can each be observed independently in the simulated world.

Requirements:
1. Each sub-question must be specific enough to map to relevant agent behavior or events.
2. The sub-questions should cover different dimensions of the original question
   such as who, what, why, how, when, or where.
3. Keep the sub-questions relevant to the simulation scenario.
4. Return JSON in the format: {"sub_queries": ["sub-question 1", "sub-question 2", ...]}"""

        user_prompt = f"""Simulation scenario:
{simulation_requirement}

{f"Report context: {report_context[:500]}" if report_context else ""}

Break the following question into {max_queries} sub-questions:
{query}

Return a JSON list of sub-questions."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            sub_queries = response.get("sub_queries", [])
            # Ensure the result is a list of strings.
            return [str(sq) for sq in sub_queries[:max_queries]]
            
        except Exception as e:
            logger.warning(f"Failed to generate sub-questions: {str(e)}. Using fallback questions.")
            # Fallback to simple variants of the original question.
            return [
                query,
                f"Who are the main participants in {query}?",
                f"What are the causes and effects of {query}?",
                f"How does {query} unfold over time?"
            ][:max_queries]
    
    def panorama_search(
        self,
        graph_id: str,
        query: str,
        include_expired: bool = True,
        limit: int = 50
    ) -> PanoramaResult:
        """
        PanoramaSearch broad retrieval.

        Produces a full-picture view including all relevant content and historical or expired information:
        1. Fetch all relevant nodes
        2. Fetch all edges, including expired or invalid ones
        3. Separate current facts from historical facts

        This is useful when the report needs the full evolution of an event.
        
        Args:
            graph_id: Graph ID
            query: Search query used for relevance ranking
            include_expired: Whether to include expired content
            limit: Result limit
            
        Returns:
            PanoramaResult: Broad retrieval result
        """
        logger.info(f"PanoramaSearch broad retrieval: {query[:50]}...")
        
        result = PanoramaResult(query=query)
        
        # Fetch all nodes.
        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)
        
        # Fetch all edges, including temporal metadata.
        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)
        
        # Separate current facts from historical ones.
        active_facts = []
        historical_facts = []
        
        for edge in all_edges:
            if not edge.fact:
                continue
            
            # Node names are available if later formatting needs them.
            source_name = node_map.get(edge.source_node_uuid, NodeInfo('', '', [], '', {})).name or edge.source_node_uuid[:8]
            target_name = node_map.get(edge.target_node_uuid, NodeInfo('', '', [], '', {})).name or edge.target_node_uuid[:8]
            _ = (source_name, target_name)

            # Determine whether the fact is historical.
            is_historical = edge.is_expired or edge.is_invalid
            
            if is_historical:
                # Historical or expired fact with time markers.
                valid_at = edge.valid_at or "Unknown"
                invalid_at = edge.invalid_at or edge.expired_at or "Unknown"
                fact_with_time = f"[{valid_at} - {invalid_at}] {edge.fact}"
                historical_facts.append(fact_with_time)
            else:
                # Currently valid fact.
                active_facts.append(edge.fact)

        # Rank facts by relevance to the query.
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score
        
        # Sort and apply the limit.
        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)
        
        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)
        
        logger.info(
            f"PanoramaSearch complete: {result.active_count} active facts, "
            f"{result.historical_count} historical facts"
        )
        return result
    
    def quick_search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10
    ) -> SearchResult:
        """
        QuickSearch lightweight retrieval.

        Simple lookup flow:
        1. Call the Zep semantic search directly
        2. Return the most relevant results
        3. Use it for straightforward retrieval needs
        
        Args:
            graph_id: Graph ID
            query: Search query
            limit: Number of results to return
            
        Returns:
            SearchResult: Search results
        """
        logger.info(f"QuickSearch: {query[:50]}...")
        
        # Reuse the existing graph search directly.
        result = self.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit,
            scope="edges"
        )
        
        logger.info(f"QuickSearch complete: {result.total_count} results")
        return result
    
    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None
    ) -> InterviewResult:
        """
        Interview simulated agents in depth.

        Calls the real OASIS interview API against running simulation agents:
        1. Load agent profile files automatically
        2. Use the LLM to choose the most relevant agents
        3. Use the LLM to generate interview questions
        4. Call `/api/simulation/interview/batch` for a real interview run
        5. Consolidate the results into an interview report

        Important: the simulation environment must still be running.

        Best for:
        - understanding the event from different roles
        - collecting diverse viewpoints
        - retrieving real agent answers rather than synthetic summaries
        
        Args:
            simulation_id: Simulation ID used to locate profiles and call the interview API
            interview_requirement: Unstructured interview goal, such as "understand how students see the event"
            simulation_requirement: Optional simulation background
            max_agents: Maximum number of agents to interview
            custom_questions: Optional custom questions; auto-generated if omitted
            
        Returns:
            InterviewResult: Interview results
        """
        from .simulation_runner import SimulationRunner
        
        logger.info(f"InterviewAgents (real API): {interview_requirement[:50]}...")
        
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or []
        )
        
        # Step 1: Load agent profile files.
        profiles = self._load_agent_profiles(simulation_id)
        
        if not profiles:
            logger.warning(f"No agent profile files found for simulation {simulation_id}")
            result.summary = "No interviewable agent profile files were found."
            return result
        
        result.total_agents = len(profiles)
        logger.info(f"Loaded {len(profiles)} agent profiles")
        
        # Step 2: Use the LLM to choose which agents to interview.
        selected_agents, selected_indices, selection_reasoning = self._select_agents_for_interview(
            profiles=profiles,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents
        )
        
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning
        logger.info(f"Selected {len(selected_agents)} agents for interviews: {selected_indices}")
        
        # Step 3: Generate interview questions if needed.
        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents
            )
            logger.info(f"Generated {len(result.interview_questions)} interview questions")
        
        # Combine questions into a single prompt.
        combined_prompt = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)])
        
        # Add a prefix that constrains the response format.
        INTERVIEW_PROMPT_PREFIX = (
            "You are being interviewed. Answer the questions below directly in plain text, "
            "using your role, memory, and prior actions as context.\n"
            "Response requirements:\n"
            "1. Answer directly in natural language and do not call tools\n"
            "2. Do not return JSON or tool-call payloads\n"
            "3. Do not use Markdown headings such as #, ##, or ###\n"
            "4. Answer each numbered question in order, starting each answer with \"Question X:\"\n"
            "5. Separate answers with a blank line\n"
            "6. Give substantive answers, with at least 2-3 sentences per question\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"
        
        # Step 4: Call the real interview API in dual-platform mode.
        try:
            # Build the batch interview request.
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt  # Use the constrained prompt above.
                    # No platform specified: the API will interview both Twitter and Reddit personas.
                })
            
            logger.info(f"Calling batch interview API in dual-platform mode for {len(interviews_request)} agents")
            
            # Use SimulationRunner's batch interview helper without a platform override.
            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,  # Unspecified means dual-platform mode.
                timeout=180.0   # Dual-platform interviews need a longer timeout.
            )
            
            logger.info(f"Interview API returned {api_result.get('interviews_count', 0)} results, success={api_result.get('success')}")
            
            # Check whether the API call succeeded.
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "Unknown error")
                logger.warning(f"Interview API call failed: {error_msg}")
                result.summary = f"Interview API call failed: {error_msg}. Check the OASIS simulation environment status."
                return result
            
            # Step 5: Parse the API response and build AgentInterview objects.
            # Dual-platform mode returns keys such as {"twitter_0": {...}, "reddit_0": {...}}.
            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}
            
            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "Unknown")
                agent_bio = agent.get("bio", "")
                
                # Fetch the agent's results from both platforms.
                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                
                twitter_response = twitter_result.get("response", "")
                reddit_response = reddit_result.get("response", "")

                # Strip any accidental tool-call JSON wrappers.
                twitter_response = self._clean_tool_call_response(twitter_response)
                reddit_response = self._clean_tool_call_response(reddit_response)

                # Always emit both platform sections.
                twitter_text = twitter_response if twitter_response else "[No reply from this platform]"
                reddit_text = reddit_response if reddit_response else "[No reply from this platform]"
                response_text = f"[Twitter response]\n{twitter_text}\n\n[Reddit response]\n{reddit_text}"

                # Extract key quotes from both platform responses.
                import re
                combined_responses = f"{twitter_response} {reddit_response}"

                # Clean response text by removing labels, numbering, and markdown noise.
                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r'\u95ee\u9898\d+[\uFF1A:]\s*', '', clean_text)
                clean_text = re.sub(r'\u3010[^\u3011]+\u3011', '', clean_text)

                # Strategy 1: prefer complete, substantive sentences.
                sentences = re.split(r'[\u3002\uFF01\uFF1F]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W\uFF0C,;\uFF1B:\uFF1A\u3001]+', s.strip())
                    and not s.strip().startswith(('{', '\u95ee\u9898'))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "\u3002" for s in meaningful[:3]]

                # Strategy 2: fall back to long passages inside paired quotes.
                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[\uFF0C,;\uFF1B:\uFF1A\u3001]', q)][:3]
                
                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],  # Keep a longer bio excerpt.
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5]
                )
                result.interviews.append(interview)
            
            result.interviewed_count = len(result.interviews)
            
        except ValueError as e:
            # The simulation environment is probably not running.
            logger.warning(f"Interview API call failed (environment not running?): {e}")
            result.summary = (
                f"Interview failed: {str(e)}. The simulation environment may be closed. "
                "Make sure OASIS is still running."
            )
            return result
        except Exception as e:
            logger.error(f"Interview API call raised an exception: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result.summary = f"An error occurred during the interview flow: {str(e)}"
            return result
        
        # Step 6: Generate the interview summary.
        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement
            )
        
        logger.info(f"InterviewAgents complete: interviewed {result.interviewed_count} agents in dual-platform mode")
        return result
    
    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        """Strip JSON tool-call wrappers from an agent response and return the real text."""
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        """Load agent profile files for a simulation."""
        import os
        import csv
        
        # Build the profile directory path.
        sim_dir = os.path.join(
            os.path.dirname(__file__), 
            f'../../uploads/simulations/{simulation_id}'
        )
        
        profiles = []
        
        # Prefer the Reddit JSON profile file first.
        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                logger.info(f"Loaded {len(profiles)} profiles from reddit_profiles.json")
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read reddit_profiles.json: {e}")
        
        # Fall back to the Twitter CSV profile file.
        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Convert CSV rows into the common profile format.
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "Unknown"
                        })
                logger.info(f"Loaded {len(profiles)} profiles from twitter_profiles.csv")
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read twitter_profiles.csv: {e}")
        
        return profiles
    
    def _select_agents_for_interview(
        self,
        profiles: List[Dict[str, Any]],
        interview_requirement: str,
        simulation_requirement: str,
        max_agents: int
    ) -> tuple:
        """
        Use the LLM to choose which agents to interview.
        
        Returns:
            tuple: (selected_agents, selected_indices, reasoning)
                - selected_agents: full data for the selected agents
                - selected_indices: selected agent indices for API calls
                - reasoning: why they were chosen
        """
        
        # Build concise agent summaries for the LLM.
        agent_summaries = []
        for i, profile in enumerate(profiles):
            summary = {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "Unknown"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", [])
            }
            agent_summaries.append(summary)
        
        system_prompt = """You are an expert interview producer. Based on the interview goal,
select the most suitable agents from the simulation roster.

Selection criteria:
1. The agent's identity or profession is relevant to the interview topic.
2. The agent is likely to hold a distinct or valuable perspective.
3. Prefer a diverse set of viewpoints, such as support, opposition, neutrality, or expertise.
4. Prioritize roles that are directly connected to the event.

Return JSON in the format:
{
    "selected_indices": [selected agent indices],
    "reasoning": "explanation of why they were selected"
}"""

        user_prompt = f"""Interview goal:
{interview_requirement}

Simulation background:
{simulation_requirement if simulation_requirement else "Not provided"}

Available agents ({len(agent_summaries)} total):
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

Choose up to {max_agents} agents who are the best fit for the interview, and explain why."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Selected automatically based on relevance")
            
            # Resolve the full agent objects for the selected indices.
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            
            return selected_agents, valid_indices, reasoning
            
        except Exception as e:
            logger.warning(f"LLM agent selection failed, using fallback selection: {e}")
            # Fallback to the first N agents.
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Used the default fallback selection strategy"
    
    def _generate_interview_questions(
        self,
        interview_requirement: str,
        simulation_requirement: str,
        selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate interview questions with the LLM."""
        
        agent_roles = [a.get("profession", "Unknown") for a in selected_agents]
        
        system_prompt = """You are a professional interviewer. Generate 3-5 deep interview questions
based on the interview goal.

Question requirements:
1. Use open-ended questions that invite detailed answers.
2. Make room for different roles to answer differently.
3. Cover facts, opinions, and feelings across multiple dimensions.
4. Keep the phrasing natural, like a real interview.
5. Keep each question concise.
6. Ask directly without adding background setup or prefixes.

Return JSON in the format: {"questions": ["Question 1", "Question 2", ...]}"""

        user_prompt = f"""Interview goal: {interview_requirement}

Simulation background: {simulation_requirement if simulation_requirement else "Not provided"}

Interviewee roles: {', '.join(agent_roles)}

Generate 3-5 interview questions."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            return response.get("questions", [f"What is your view on {interview_requirement}?"])
            
        except Exception as e:
            logger.warning(f"Failed to generate interview questions: {e}")
            return [
                f"What is your perspective on {interview_requirement}?",
                "How does this affect you or the group you represent?",
                "What do you think should be done to address or improve the situation?"
            ]
    
    def _generate_interview_summary(
        self,
        interviews: List[AgentInterview],
        interview_requirement: str
    ) -> str:
        """Generate an interview summary."""
        
        if not interviews:
            return "No interviews were completed."
        
        # Collect interview excerpts.
        interview_texts = []
        for interview in interviews:
            interview_texts.append(f"[{interview.agent_name} ({interview.agent_role})]\n{interview.response[:500]}")
        
        system_prompt = """You are a professional news editor. Based on multiple interview answers,
write a concise interview summary.

Summary requirements:
1. Distill the main viewpoints across participants.
2. Identify areas of consensus and disagreement.
3. Highlight valuable quotes when useful.
4. Stay objective and neutral.
5. Keep the summary concise.

Formatting constraints:
- Use plain-text paragraphs separated by blank lines
- Do not use Markdown headings such as #, ##, or ###
- Do not use divider lines such as --- or ***
- You may use **bold** for important keywords, but avoid other Markdown syntax"""

        user_prompt = f"""Interview topic: {interview_requirement}

Interview content:
{"".join(interview_texts)}

Generate the interview summary."""

        try:
            summary = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return summary
            
        except Exception as e:
            logger.warning(f"Failed to generate the interview summary: {e}")
            # Fallback to a simple list.
            return f"Interviewed {len(interviews)} participants, including: " + ", ".join([i.agent_name for i in interviews])
