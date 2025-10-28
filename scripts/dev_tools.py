#!/usr/bin/env python3
"""
Development tools and utilities for Project Management Agent
Provides health checks, testing, and debugging capabilities
"""

import sys
import os
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import get_logger, setup_logging_from_env
from src.utils.config import get_config
from src.utils.debug import MemoryMonitor, get_system_info, force_garbage_collection
from src.utils.errors import ProjectManagementError, error_handler


logger = get_logger(__name__)


def health_check() -> Dict[str, Any]:
    """Comprehensive health check of the system"""
    logger.info("Starting health check...")
    
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'healthy',
        'checks': {}
    }
    
    # Test API import
    try:
        from api.main import app
        health_status['checks']['api_import'] = {
            'status': 'ok',
            'message': 'API module imported successfully'
        }
    except Exception as e:
        health_status['checks']['api_import'] = {
            'status': 'error',
            'message': f'API import failed: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    # Test database models
    try:
        from database.models import User, Project, Task
        health_status['checks']['database_models'] = {
            'status': 'ok',
            'message': 'Database models imported successfully'
        }
    except Exception as e:
        health_status['checks']['database_models'] = {
            'status': 'error',
            'message': f'Database models import failed: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    # Test DeerFlow
    try:
        from src.graph.builder import build_graph
        health_status['checks']['deerflow'] = {
            'status': 'ok',
            'message': 'DeerFlow imported successfully'
        }
    except Exception as e:
        health_status['checks']['deerflow'] = {
            'status': 'error',
            'message': f'DeerFlow import failed: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    # Test conversation flow
    try:
        from src.conversation.flow_manager import ConversationFlowManager
        health_status['checks']['conversation_flow'] = {
            'status': 'ok',
            'message': 'Conversation flow imported successfully'
        }
    except Exception as e:
        health_status['checks']['conversation_flow'] = {
            'status': 'error',
            'message': f'Conversation flow import failed: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    # Test configuration
    try:
        config = get_config()
        health_status['checks']['configuration'] = {
            'status': 'ok',
            'message': 'Configuration loaded successfully'
        }
    except Exception as e:
        health_status['checks']['configuration'] = {
            'status': 'error',
            'message': f'Configuration load failed: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    # Test memory usage
    try:
        memory_monitor = MemoryMonitor()
        memory_info = memory_monitor.get_memory_usage()
        health_status['checks']['memory'] = {
            'status': 'ok',
            'message': f"Memory usage: {memory_info['percent']:.1f}%",
            'details': memory_info
        }
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'error',
            'message': f'Memory check failed: {str(e)}'
        }
    
    logger.info(f"Health check completed: {health_status['overall_status']}")
    return health_status


def test_imports() -> Dict[str, Any]:
    """Test all critical imports"""
    logger.info("Testing imports...")
    
    import_results = {
        'timestamp': datetime.now().isoformat(),
        'total_imports': 0,
        'successful_imports': 0,
        'failed_imports': 0,
        'results': {}
    }
    
    # List of critical imports to test
    imports_to_test = [
        ('api.main', 'FastAPI application'),
        ('database.models', 'Database models'),
        ('src.conversation.flow_manager', 'Conversation flow manager'),
        ('src.graph.builder', 'DeerFlow graph builder'),
        ('src.llms.llm', 'LLM utilities'),
        ('src.tools.search', 'Search tools'),
        ('src.utils.logger', 'Logging utilities'),
        ('src.utils.config', 'Configuration utilities'),
        ('src.utils.debug', 'Debug utilities'),
        ('src.utils.errors', 'Error handling utilities')
    ]
    
    for module_name, description in imports_to_test:
        import_results['total_imports'] += 1
        
        try:
            __import__(module_name)
            import_results['successful_imports'] += 1
            import_results['results'][module_name] = {
                'status': 'ok',
                'description': description
            }
        except Exception as e:
            import_results['failed_imports'] += 1
            import_results['results'][module_name] = {
                'status': 'error',
                'description': description,
                'error': str(e)
            }
    
    logger.info(f"Import test completed: {import_results['successful_imports']}/{import_results['total_imports']} successful")
    return import_results


def check_configuration() -> Dict[str, Any]:
    """Check configuration validity"""
    logger.info("Checking configuration...")
    
    try:
        config = get_config()
        
        # Check for warnings
        warnings = []
        
        if not config.llm.api_key:
            warnings.append("LLM API key not set")
        
        if not config.database.password:
            warnings.append("Database password not set")
        
        if config.api.jwt_secret == "your-secret-key-change-in-production":
            warnings.append("Using default JWT secret")
        
        config_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'ok',
            'warnings': warnings,
            'config': {
                'environment': config.environment,
                'debug': config.debug,
                'database': {
                    'host': config.database.host,
                    'port': config.database.port,
                    'name': config.database.name,
                    'user': config.database.user,
                    'password': '***' if config.database.password else '',
                    'pool_size': config.database.pool_size,
                    'max_overflow': config.database.max_overflow
                },
                'redis': {
                    'host': config.redis.host,
                    'port': config.redis.port,
                    'password': '***' if config.redis.password else '',
                    'db': config.redis.db,
                    'max_connections': config.redis.max_connections
                },
                'api': {
                    'host': config.api.host,
                    'port': config.api.port,
                    'debug': config.api.debug,
                    'cors_origins': config.api.cors_origins,
                    'jwt_algorithm': config.api.jwt_algorithm,
                    'jwt_expire_minutes': config.api.jwt_expire_minutes
                },
                'llm': {
                    'provider': config.llm.provider,
                    'api_key': '***' if config.llm.api_key else '',
                    'model': config.llm.model,
                    'temperature': config.llm.temperature,
                    'max_tokens': config.llm.max_tokens,
                    'timeout': config.llm.timeout
                },
                'search': {
                    'provider': config.search.provider,
                    'brave_api_key': '***' if config.search.brave_api_key else '',
                    'tavily_api_key': '***' if config.search.tavily_api_key else '',
                    'max_results': config.search.max_results,
                    'timeout': config.search.timeout
                },
                'logging': {
                    'level': config.logging.level,
                    'debug': config.logging.debug,
                    'log_file': config.logging.log_file,
                    'error_file': config.logging.error_file,
                    'structured_file': config.logging.structured_file
                }
            }
        }
        
        return config_status
        
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }


def generate_performance_report() -> Dict[str, Any]:
    """Generate performance report"""
    logger.info("Generating performance report...")
    
    try:
        system_info = get_system_info()
        memory_monitor = MemoryMonitor()
        memory_info = memory_monitor.get_memory_usage()
        
        performance_report = {
            'timestamp': datetime.now().isoformat(),
            'profiler_stats': {},  # Would be populated by actual profiler
            'memory_usage': memory_info,
            'request_stats': {},  # Would be populated by actual request tracking
            'error_stats': {
                'error_counts': {},
                'circuit_breakers': {}
            }
        }
        
        logger.info("Performance report generated")
        return performance_report
        
    except Exception as e:
        logger.error(f"Performance report generation failed: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }


def run_all_checks() -> Dict[str, Any]:
    """Run all development checks"""
    logger.info("Running all development checks...")
    
    start_time = time.time()
    
    # Run all checks
    health_result = health_check()
    import_result = test_imports()
    config_result = check_configuration()
    performance_result = generate_performance_report()
    
    end_time = time.time()
    
    # Compile results
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'execution_time': end_time - start_time,
        'health_check': health_result,
        'import_test': import_result,
        'config_check': config_result,
        'performance_report': performance_result,
        'overall_status': health_result['overall_status']
    }
    
    logger.info(f"All checks completed: {all_results['overall_status']}")
    return all_results


def main():
    """Main entry point for dev tools"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev_tools.py <command>")
        print("Commands: health, imports, config, performance, all")
        return
    
    command = sys.argv[1].lower()
    
    # Setup logging
    setup_logging_from_env()
    
    try:
        if command == 'health':
            result = health_check()
        elif command == 'imports':
            result = test_imports()
        elif command == 'config':
            result = check_configuration()
        elif command == 'performance':
            result = generate_performance_report()
        elif command == 'all':
            result = run_all_checks()
        else:
            print(f"Unknown command: {command}")
            return
        
        # Print results
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        error_info = error_handler(e)
        print(json.dumps(error_info, indent=2))


if __name__ == "__main__":
    main()


