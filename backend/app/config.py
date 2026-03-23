"""
Configuration management.
Loads configuration consistently from the repository root `.env` file.
"""

import os
from dotenv import load_dotenv

# Load the repository root `.env` file
# Path: `MiroFish/.env` (relative to `backend/app/config.py`)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If the repository root does not have a `.env`, fall back to environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:3000')
    AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:5002')
    AUTH_SESSION_ENDPOINT = os.environ.get('AUTH_SESSION_ENDPOINT', f'{AUTH_SERVICE_URL}/api/session')
    AUTH_SESSION_TIMEOUT = float(os.environ.get('AUTH_SESSION_TIMEOUT', '5'))
    
    # JSON settings - disable ASCII escaping so non-ASCII text is emitted directly instead of as \uXXXX escapes
    JSON_AS_ASCII = False
    
    # LLM settings (using the OpenAI-compatible format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep settings
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Firecrawl website ingestion settings
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
    FIRECRAWL_BASE_URL = os.environ.get('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev')
    FIRECRAWL_CRAWL_LIMIT = int(os.environ.get('FIRECRAWL_CRAWL_LIMIT', '20'))
    FIRECRAWL_MAX_DISCOVERY_DEPTH = int(os.environ.get('FIRECRAWL_MAX_DISCOVERY_DEPTH', '2'))
    FIRECRAWL_TIMEOUT_SECONDS = int(os.environ.get('FIRECRAWL_TIMEOUT_SECONDS', '90'))
    FIRECRAWL_POLL_INTERVAL_SECONDS = float(os.environ.get('FIRECRAWL_POLL_INTERVAL_SECONDS', '2'))
    FIRECRAWL_MIN_PAGE_WORDS = int(os.environ.get('FIRECRAWL_MIN_PAGE_WORDS', '80'))
    FIRECRAWL_MAX_PAGE_CHARACTERS = int(os.environ.get('FIRECRAWL_MAX_PAGE_CHARACTERS', '12000'))
    
    # Text processing settings
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default overlap size
    
    # OASIS simulation settings
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # Available OASIS platform actions
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent settings
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def get_cors_origins(cls):
        """Return the list of frontend origins allowed to access the backend API."""
        raw_origins = os.environ.get('BACKEND_CORS_ORIGINS')
        if raw_origins:
            origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
            if origins:
                return origins

        return [cls.FRONTEND_ORIGIN, 'http://127.0.0.1:3000']
    
    @classmethod
    def validate(cls):
        """Validate required configuration values."""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        return errors
