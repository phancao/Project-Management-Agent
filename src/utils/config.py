"""
Configuration management system for Project Management Agent
Provides environment-based, type-safe configuration with validation
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    name: str = "project_management"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 10


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30


@dataclass
class SearchConfig:
    """Search configuration"""
    provider: str = "duckduckgo"
    brave_api_key: str = ""
    tavily_api_key: str = ""
    max_results: int = 10
    timeout: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    debug: bool = False
    log_file: str = "logs/app.log"
    error_file: str = "logs/error.log"
    structured_file: str = "logs/structured.log"


@dataclass
class Config:
    """Main configuration class"""
    environment: str = "development"
    debug: bool = False
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    api: APIConfig = field(default_factory=APIConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def __post_init__(self):
        """Load configuration from environment and files"""
        self._load_from_env()
        self._load_from_yaml()
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Environment
        self.environment = os.getenv('ENVIRONMENT', self.environment)
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Database
        self.database.host = os.getenv('DB_HOST', self.database.host)
        self.database.port = int(os.getenv('DB_PORT', str(self.database.port)))
        self.database.name = os.getenv('DB_NAME', self.database.name)
        self.database.user = os.getenv('DB_USER', self.database.user)
        self.database.password = os.getenv('DB_PASSWORD', self.database.password)
        self.database.pool_size = int(os.getenv('DB_POOL_SIZE', str(self.database.pool_size)))
        self.database.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', str(self.database.max_overflow)))
        
        # Redis
        self.redis.host = os.getenv('REDIS_HOST', self.redis.host)
        self.redis.port = int(os.getenv('REDIS_PORT', str(self.redis.port)))
        self.redis.password = os.getenv('REDIS_PASSWORD', self.redis.password)
        self.redis.db = int(os.getenv('REDIS_DB', str(self.redis.db)))
        self.redis.max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', str(self.redis.max_connections)))
        
        # API
        self.api.host = os.getenv('API_HOST', self.api.host)
        self.api.port = int(os.getenv('API_PORT', str(self.api.port)))
        self.api.debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
        self.api.jwt_secret = os.getenv('JWT_SECRET', self.api.jwt_secret)
        self.api.jwt_algorithm = os.getenv('JWT_ALGORITHM', self.api.jwt_algorithm)
        self.api.jwt_expire_minutes = int(os.getenv('JWT_EXPIRE_MINUTES', str(self.api.jwt_expire_minutes)))
        
        # LLM
        self.llm.provider = os.getenv('LLM_PROVIDER', self.llm.provider)
        self.llm.api_key = os.getenv('LLM_API_KEY', self.llm.api_key)
        self.llm.model = os.getenv('LLM_MODEL', self.llm.model)
        self.llm.temperature = float(os.getenv('LLM_TEMPERATURE', str(self.llm.temperature)))
        self.llm.max_tokens = int(os.getenv('LLM_MAX_TOKENS', str(self.llm.max_tokens)))
        self.llm.timeout = int(os.getenv('LLM_TIMEOUT', str(self.llm.timeout)))
        
        # Search
        self.search.provider = os.getenv('SEARCH_PROVIDER', self.search.provider)
        self.search.brave_api_key = os.getenv('BRAVE_API_KEY', self.search.brave_api_key)
        self.search.tavily_api_key = os.getenv('TAVILY_API_KEY', self.search.tavily_api_key)
        self.search.max_results = int(os.getenv('SEARCH_MAX_RESULTS', str(self.search.max_results)))
        self.search.timeout = int(os.getenv('SEARCH_TIMEOUT', str(self.search.timeout)))
        
        # Logging
        self.logging.level = os.getenv('LOG_LEVEL', self.logging.level)
        self.logging.debug = os.getenv('LOG_DEBUG', 'false').lower() == 'true'
        self.logging.log_file = os.getenv('LOG_FILE', self.logging.log_file)
        self.logging.error_file = os.getenv('ERROR_FILE', self.logging.error_file)
        self.logging.structured_file = os.getenv('STRUCTURED_FILE', self.logging.structured_file)
    
    def _load_from_yaml(self):
        """Load configuration from YAML files"""
        config_dir = Path('config')
        if not config_dir.exists():
            return
        
        env_file = config_dir / f'{self.environment}.yaml'
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    self._merge_yaml_config(yaml_config)
            except Exception as e:
                print(f"Warning: Could not load YAML config from {env_file}: {e}")
    
    def _merge_yaml_config(self, yaml_config: Dict[str, Any]):
        """Merge YAML configuration into current config"""
        if not yaml_config:
            return
        
        # Merge database config
        if 'database' in yaml_config:
            db_config = yaml_config['database']
            for key, value in db_config.items():
                if hasattr(self.database, key):
                    setattr(self.database, key, value)
        
        # Merge redis config
        if 'redis' in yaml_config:
            redis_config = yaml_config['redis']
            for key, value in redis_config.items():
                if hasattr(self.redis, key):
                    setattr(self.redis, key, value)
        
        # Merge API config
        if 'api' in yaml_config:
            api_config = yaml_config['api']
            for key, value in api_config.items():
                if hasattr(self.api, key):
                    setattr(self.api, key, value)
        
        # Merge LLM config
        if 'llm' in yaml_config:
            llm_config = yaml_config['llm']
            for key, value in llm_config.items():
                if hasattr(self.llm, key):
                    setattr(self.llm, key, value)
        
        # Merge search config
        if 'search' in yaml_config:
            search_config = yaml_config['search']
            for key, value in search_config.items():
                if hasattr(self.search, key):
                    setattr(self.search, key, value)
        
        # Merge logging config
        if 'logging' in yaml_config:
            logging_config = yaml_config['logging']
            for key, value in logging_config.items():
                if hasattr(self.logging, key):
                    setattr(self.logging, key, value)
    
    def _validate(self):
        """Validate configuration"""
        warnings = []
        
        # Check required fields
        if not self.llm.api_key and self.environment == 'production':
            warnings.append("LLM API key not set")
        
        if not self.database.password and self.environment == 'production':
            warnings.append("Database password not set")
        
        if self.api.jwt_secret == "your-secret-key-change-in-production":
            warnings.append("Using default JWT secret")
        
        # Log warnings
        if warnings:
            print("Configuration warnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """Reload configuration from environment and files"""
    global _config
    _config = None
    return get_config()


