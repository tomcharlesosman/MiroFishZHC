"""
JunoFish Backend - Flask application factory
"""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings (for example from third-party libraries such as transformers)
# This must be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, g, request
from flask_cors import CORS

from .config import Config
from .services.auth_session import AuthServiceUnavailable, fetch_session
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure JSON encoding so non-ASCII text is emitted directly instead of as \uXXXX escapes
    # Flask >= 2.3 uses app.json.ensure_ascii; older versions use JSON_AS_ASCII
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Configure logging
    logger = setup_logger('mirofish')
    
    # Only print startup information in the reloader subprocess to avoid duplicate logs in debug mode
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("JunoFish Backend starting up...")
        logger.info("=" * 50)
    
    # Enable CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": Config.get_cors_origins()}},
        supports_credentials=True
    )
    
    # Register the simulation cleanup hook so all simulation processes are terminated when the server shuts down
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Registered simulation cleanup hook")
    
    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")

    @app.before_request
    def require_authenticated_session():
        if request.method == 'OPTIONS':
            return None

        if not request.path.startswith('/api/'):
            return None

        cookie_header = request.headers.get('Cookie')
        if not cookie_header:
            return {'success': False, 'error': 'Authentication required'}, 401

        try:
            session = fetch_session(cookie_header)
        except AuthServiceUnavailable:
            logger = get_logger('mirofish.auth')
            logger.exception('Authentication service unavailable')
            return {'success': False, 'error': 'Authentication service unavailable'}, 503

        if not session:
            return {'success': False, 'error': 'Authentication required'}, 401

        g.current_user = session.get('user')
        g.current_session = session.get('session')
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"Response: {response.status_code}")
        return response
    
    # Register blueprints
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    
    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'JunoFish Backend'}
    
    if should_log_startup:
        logger.info("JunoFish Backend startup complete")
    
    return app
