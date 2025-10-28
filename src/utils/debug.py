"""
Debug utilities for Project Management Agent
Provides performance profiling, memory monitoring, and debugging tools
"""

import time
import psutil
import functools
import tracemalloc
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager
import threading
import gc


class MemoryMonitor:
    """Memory usage monitoring utility"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.peak_memory = self.initial_memory
        self.monitoring = False
        self._monitor_thread = None
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage in MB"""
        memory_info = self.process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent()
        }
    
    def start_monitoring(self, interval: float = 1.0):
        """Start continuous memory monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self, interval: float):
        """Memory monitoring loop"""
        while self.monitoring:
            current_memory = self.get_memory_usage()
            if current_memory['rss'] > self.peak_memory['rss']:
                self.peak_memory = current_memory
            time.sleep(interval)
    
    def get_peak_memory(self) -> Dict[str, float]:
        """Get peak memory usage"""
        return self.peak_memory
    
    def reset_peak(self):
        """Reset peak memory tracking"""
        self.peak_memory = self.get_memory_usage()


# Global memory monitor
_memory_monitor = MemoryMonitor()


def profile_function(func: Callable) -> Callable:
    """
    Decorator to profile function execution time and memory usage
    
    Args:
        func: Function to profile
    
    Returns:
        Wrapped function with profiling
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = _memory_monitor.get_memory_usage()
        
        # Start memory monitoring
        _memory_monitor.start_monitoring(0.1)
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = _memory_monitor.get_memory_usage()
            peak_memory = _memory_monitor.get_peak_memory()
            
            # Stop monitoring
            _memory_monitor.stop_monitoring()
            
            # Log performance metrics
            duration = end_time - start_time
            memory_delta = end_memory['rss'] - start_memory['rss']
            
            print(f"🔍 Function: {func.__name__}")
            print(f"   ⏱️  Duration: {duration:.3f}s")
            print(f"   💾 Memory delta: {memory_delta:+.2f}MB")
            print(f"   📈 Peak memory: {peak_memory['rss']:.2f}MB")
            print(f"   📊 Memory percent: {peak_memory['percent']:.2f}%")
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = _memory_monitor.get_memory_usage()
        
        # Start memory monitoring
        _memory_monitor.start_monitoring(0.1)
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = _memory_monitor.get_memory_usage()
            peak_memory = _memory_monitor.get_peak_memory()
            
            # Stop monitoring
            _memory_monitor.stop_monitoring()
            
            # Log performance metrics
            duration = end_time - start_time
            memory_delta = end_memory['rss'] - start_memory['rss']
            
            print(f"🔍 Async Function: {func.__name__}")
            print(f"   ⏱️  Duration: {duration:.3f}s")
            print(f"   💾 Memory delta: {memory_delta:+.2f}MB")
            print(f"   📈 Peak memory: {peak_memory['rss']:.2f}MB")
            print(f"   📊 Memory percent: {peak_memory['percent']:.2f}%")
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


@contextmanager
def memory_trace():
    """Context manager for memory tracing"""
    tracemalloc.start()
    try:
        yield
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"🔍 Memory trace - Current: {current / 1024 / 1024:.2f}MB, Peak: {peak / 1024 / 1024:.2f}MB")


def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging"""
    return {
        'cpu_count': psutil.cpu_count(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory()._asdict(),
        'disk': psutil.disk_usage('/')._asdict(),
        'process_memory': _memory_monitor.get_memory_usage(),
        'python_memory': {
            'gc_counts': gc.get_count(),
            'gc_threshold': gc.get_threshold()
        }
    }


def force_garbage_collection():
    """Force garbage collection and return collected objects count"""
    collected = gc.collect()
    print(f"🗑️  Garbage collection: {collected} objects collected")
    return collected


def print_memory_usage():
    """Print current memory usage"""
    memory = _memory_monitor.get_memory_usage()
    print(f"💾 Memory Usage:")
    print(f"   RSS: {memory['rss']:.2f}MB")
    print(f"   VMS: {memory['vms']:.2f}MB")
    print(f"   Percent: {memory['percent']:.2f}%")


# Import asyncio for the decorator
import asyncio


