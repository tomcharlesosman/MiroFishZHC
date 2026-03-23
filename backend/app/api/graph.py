"""
Graph-related API routes.
Uses the project-context mechanism to persist state on the server.
"""

import os
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.firecrawl_ingestion import FirecrawlIngestionError, FirecrawlIngestionService
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get the logger
logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """Check whether the file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


def _format_uploaded_document_block(filename: str, text: str) -> str:
    return (
        "=== Uploaded Document ===\n"
        "Source Type: Uploaded Document\n"
        f"Document Name: {filename}\n\n"
        f"{text}"
    ).strip()


def _build_source_context(project, crawl_warnings):
    lines = [
        "Source Attribution Summary:",
        f"- Simulation requirement: {project.simulation_requirement or 'Not provided'}",
    ]

    if project.company_website_url:
        lines.extend([
            f"- Website root URL: {project.company_website_url}",
            f"- Crawl status: {project.crawl_status or 'not_started'}",
            f"- Crawled page count: {project.crawl_page_count}",
        ])
        if project.crawl_pages:
            preview = project.crawl_pages[:10]
            lines.append("- Website-derived evidence pages:")
            lines.extend([f"  - {url}" for url in preview])
            if len(project.crawl_pages) > len(preview):
                lines.append(f"  - ...and {len(project.crawl_pages) - len(preview)} more pages")

    if project.files:
        lines.append("- Uploaded document evidence:")
        lines.extend([f"  - {item.get('filename', 'Unknown file')}" for item in project.files])
    else:
        lines.append("- Uploaded document evidence: none")

    if crawl_warnings:
        lines.append("- Crawl caveats:")
        lines.extend([f"  - {warning}" for warning in crawl_warnings[:10]])

    return "\n".join(lines)


# ============== Project management endpoints ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """Get project details."""
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """List all projects."""
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """Delete a project."""
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Project not found or could not be deleted: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """Reset the project state (used to rebuild the graph)."""
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404
    
    # Reset to the ontology-generated state
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Endpoint 1: upload files and generate ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    Endpoint 1: upload files and analyze them to generate an ontology definition.

    Request type: multipart/form-data

    Parameters:
        files: Uploaded files (PDF/MD/TXT), multiple allowed
        simulation_requirement: Simulation requirement description (required)
        project_name: Project name (optional)
        additional_context: Additional notes (optional)

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    project = None
    try:
        logger.info("=== Start ontology generation ===")
        
        # Read parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')
        company_website_url = request.form.get('company_website_url', '')
        
        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Simulation requirement: {simulation_requirement[:100]}...")
        
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Please provide simulation_requirement"
            }), 400
        
        # Read uploaded files
        uploaded_files = request.files.getlist('files')
        has_uploaded_files = any(file and file.filename for file in uploaded_files)
        has_company_website_url = bool(company_website_url.strip())

        if not has_uploaded_files and not has_company_website_url:
            return jsonify({
                "success": False,
                "error": "Provide a company website URL or upload at least one document file."
            }), 400
        
        # Create the project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        crawl_warnings = []
        logger.info(f"Created project: {project.project_id}")
        
        # Save files and extract text
        document_texts = []
        all_text = ""

        if has_company_website_url:
            ingestion_service = FirecrawlIngestionService()
            ingestion_result = ingestion_service.crawl(company_website_url)
            project.company_website_url = ingestion_result.normalized_url
            project.crawl_status = ingestion_result.crawl_status
            project.crawl_page_count = ingestion_result.page_count
            project.crawl_pages = ingestion_result.page_urls
            crawl_warnings = ingestion_result.warnings
            document_texts.extend(ingestion_result.document_texts)
            all_text += ingestion_result.combined_text
            logger.info(
                "Website ingestion completed for project %s: %s pages (%s)",
                project.project_id,
                ingestion_result.page_count,
                ingestion_result.crawl_status,
            )
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Save the file to the project directory
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                # Extract text
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                formatted_text = _format_uploaded_document_block(file_info["original_filename"], text)
                document_texts.append(formatted_text)
                if all_text:
                    all_text += "\n\n"
                all_text += formatted_text
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "No source content was processed successfully. Check the website URL or uploaded file formats."
            }), 400
        
        # Save the extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction completed: {len(all_text)} characters")

        source_context = _build_source_context(project, crawl_warnings)
        merged_additional_context = source_context
        if additional_context:
            merged_additional_context = f"{source_context}\n\nAdditional Context:\n{additional_context}"
        
        # Generate the ontology
        logger.info("Calling LLM to generate ontology...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=merged_additional_context
        )
        
        # Save the ontology to the project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generation completed: {entity_count} entity types, {edge_count} relation types")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation completed === Project ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length,
                "company_website_url": project.company_website_url,
                "crawl_status": project.crawl_status,
                "crawl_page_count": project.crawl_page_count,
                "crawl_pages": project.crawl_pages,
                "crawl_warnings": crawl_warnings
            }
        })
        
    except FirecrawlIngestionError as e:
        if project:
            ProjectManager.delete_project(project.project_id)
        logger.error(f"Website ingestion failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        if project:
            ProjectManager.delete_project(project.project_id)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Endpoint 2: build graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    Endpoint 2: build a graph from a project_id.

    Request (JSON):
        {
            "project_id": "proj_xxxx",  // Required, from endpoint 1
            "graph_name": "Graph name", // Optional
            "chunk_size": 500,          // Optional, default 500
            "chunk_overlap": 50         // Optional, default 50
        }

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph build has started"
            }
        }
    """
    try:
        logger.info("=== Starting graph build ===")
        
        # Check configuration
        errors = []
        if not Config.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        if errors:
            logger.error(f"Configuration error: {errors}")
            return jsonify({
                "success": False,
                "error": "Configuration error: " + "; ".join(errors)
            }), 500
        
        # Parse request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request parameters: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400
        
        # Get the project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project not found: {project_id}"
            }), 404
        
        # Check project status
        force = data.get('force', False)  # Force rebuild
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "Ontology has not been generated for this project yet. Call /ontology/generate first."
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "A graph build is already in progress. To force a rebuild, set force: true.",
                "task_id": project.graph_build_task_id
            }), 400
        
        # If rebuilding is forced, reset the state
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = data.get('graph_name', project.name or 'JunoFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "No extracted text content was found"
            }), 400
        
        # Get the ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "No ontology definition was found"
            }), 400
        
        # Create an async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Created graph build task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Start the background task
        def build_task():
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph builder..."
                )
                
                # Create the graph building service
                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
                
                # Split into chunks
                task_manager.update_task(
                    task_id,
                    message="Chunking text...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                # Create the graph
                task_manager.update_task(
                    task_id,
                    message="Creating Zep graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # Update the project's graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # Set the ontology
                task_manager.update_task(
                    task_id,
                    message="Applying ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (`progress_callback` signature is `(msg, progress_ratio)`)
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"Adding {total_chunks} text chunks...",
                    progress=15
                )
                
                episode_uuids = builder.add_text_batches(
                    graph_id, 
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )
                
                # Wait for Zep processing to complete (query each episode's processed state)
                task_manager.update_task(
                    task_id,
                    message="Waiting for Zep to process the data...",
                    progress=55
                )
                
                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                builder._wait_for_episodes(episode_uuids, wait_progress_callback)
                
                # Fetch graph data
                task_manager.update_task(
                    task_id,
                    message="Fetching graph data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # Update the project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] Graph build completed: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")
                
                # Complete
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph build completed",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # Update the project status to failed
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=traceback.format_exc()
                )
        
        # Start the background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph build has started. Check /task/{task_id} for progress."
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Task query endpoints ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """Query task status."""
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks."""
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== Graph data endpoints ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """Get graph data (nodes and edges)."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is not configured"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """Delete the Zep graph."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY is not configured"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
