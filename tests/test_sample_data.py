"""
Data generation tests - creates rich sample data in the test database.
These tests are designed to populate the database with varied, realistic log data
for inspection and demonstration purposes.
"""

import pytest
from datetime import datetime
import random


class TestSampleDataGeneration:
    """Generate diverse sample data for database inspection."""
    
    def test_generate_user_activity_logs(self, logger):
        """Generate realistic user activity logs."""
        users = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry"]
        actions = ["login", "logout", "view_profile", "edit_profile", "upload_file", 
                   "download_file", "search", "comment", "like", "share", "delete"]
        
        for i in range(50):
            user = random.choice(users)
            action = random.choice(actions)
            ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
            
            metadata = {
                "session_duration": random.randint(60, 3600),
                "page_views": random.randint(1, 50),
                "device": random.choice(["desktop", "mobile", "tablet"]),
                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"])
            }
            
            logger.info(
                f"User {user} performed {action}",
                category="user_actions",
                user_id=f"user_{user}",
                action=action,
                ip_address=ip,
                metadata=metadata
            )
        
        # Verify logs were created
        results = logger.query(category="user_actions")
        assert len(results) >= 50
    
    def test_generate_error_scenarios(self, logger):
        """Generate various error scenarios."""
        error_scenarios = [
            (400, "Bad Request", "Invalid JSON in request body", "low"),
            (401, "Unauthorized", "Authentication token expired", "medium"),
            (403, "Forbidden", "Insufficient permissions to access resource", "medium"),
            (404, "Not Found", "Resource does not exist", "low"),
            (408, "Request Timeout", "Client request timed out", "medium"),
            (429, "Too Many Requests", "Rate limit exceeded", "medium"),
            (500, "Internal Server Error", "Unhandled exception in payment processor", "critical"),
            (502, "Bad Gateway", "Upstream service not responding", "high"),
            (503, "Service Unavailable", "Database connection pool exhausted", "critical"),
            (504, "Gateway Timeout", "External API call timeout", "high"),
        ]
        
        for _ in range(30):
            code, title, message, severity = random.choice(error_scenarios)
            
            stack_trace = None
            if severity in ["critical", "high"]:
                stack_trace = f"""
Traceback (most recent call last):
  File "app/main.py", line {random.randint(10, 500)}, in process_request
    result = handler.execute()
  File "app/handlers.py", line {random.randint(10, 300)}, in execute
    raise {title.replace(' ', '')}("{message}")
{title.replace(' ', '')}: {message}
                """.strip()
            
            logger.error(
                f"HTTP {code}: {title}",
                category="errors",
                error_code=code,
                error_message=message,
                stack_trace=stack_trace,
                severity=severity
            )
        
        # Verify errors were logged
        results = logger.query(category="errors")
        assert len(results) >= 30
    
    def test_generate_system_events(self, logger):
        """Generate system monitoring events."""
        event_types = [
            ("startup", "Application started successfully"),
            ("shutdown", "Application shutting down gracefully"),
            ("database_backup", "Automated database backup completed"),
            ("cache_clear", "Cache cleared successfully"),
            ("scheduled_task", "Scheduled maintenance task executed"),
            ("health_check", "System health check passed"),
            ("config_reload", "Configuration reloaded"),
            ("deployment", "New version deployed"),
            ("rollback", "Rolled back to previous version"),
            ("migration", "Database migration completed"),
        ]
        
        for _ in range(40):
            event_type, description = random.choice(event_types)
            duration = random.uniform(10.0, 5000.0) if random.random() > 0.3 else None
            
            log_level = "INFO"
            if "failed" in description.lower() or "error" in description.lower():
                log_level = "ERROR"
            elif duration and duration > 3000:
                log_level = "WARNING"
                description += " (slow execution)"
            
            if log_level == "ERROR":
                logger.error(description, category="system_events",
                           event_type=event_type, description=description,
                           duration_ms=duration)
            elif log_level == "WARNING":
                logger.warning(description, category="system_events",
                             event_type=event_type, description=description,
                             duration_ms=duration)
            else:
                logger.info(description, category="system_events",
                          event_type=event_type, description=description,
                          duration_ms=duration)
        
        # Verify events were logged
        results = logger.query(category="system_events")
        assert len(results) >= 40
    
    def test_generate_api_request_logs(self, logger):
        """Generate API request logs."""
        endpoints = [
            "/api/v1/users",
            "/api/v1/users/{id}",
            "/api/v1/posts",
            "/api/v1/posts/{id}",
            "/api/v1/comments",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/profile",
            "/api/v1/settings",
            "/api/v1/notifications",
        ]
        
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for _ in range(100):
            endpoint = random.choice(endpoints)
            method = random.choice(methods)
            
            # Most requests are successful
            if random.random() > 0.15:
                status_code = random.choice([200, 200, 200, 201, 204])
                response_time = random.uniform(10.0, 500.0)
            else:
                status_code = random.choice([400, 401, 404, 500, 503])
                response_time = random.uniform(50.0, 3000.0)
            
            request_body = None
            response_body = None
            
            if method in ["POST", "PUT", "PATCH"]:
                request_body = {
                    "data": {"field": "value"},
                    "timestamp": datetime.now().isoformat()
                }
            
            if 200 <= status_code < 300:
                response_body = {
                    "success": True,
                    "data": {"id": random.randint(1, 1000)},
                    "message": "Request successful"
                }
            else:
                response_body = {
                    "success": False,
                    "error": "Request failed",
                    "code": status_code
                }
            
            logger.info(
                f"{method} {endpoint} - {status_code}",
                category="api_requests",
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time,
                request_body=request_body,
                response_body=response_body
            )
        
        # Verify API requests were logged
        results = logger.query(category="api_requests")
        assert len(results) >= 100


class TestComplexScenarios:
    """Test complex, real-world scenarios."""
    
    def test_user_journey_with_error(self, logger):
        """Simulate a complete user journey including an error."""
        user_id = "user_test_journey"
        session_id = "sess_12345"
        
        # User logs in
        logger.info("User login", category="user_actions",
                   user_id=user_id, action="login",
                   ip_address="203.0.113.42",
                   metadata={"session_id": session_id, "2fa_enabled": True})
        
        # Browse content
        for i in range(5):
            logger.info(f"View content {i}", category="user_actions",
                       user_id=user_id, action="view_content",
                       metadata={"content_id": f"post_{i}", "session_id": session_id})
        
        # Attempt to upload file - fails
        logger.error("File upload failed", category="errors",
                    error_code=413,
                    error_message="File size exceeds maximum allowed size of 10MB",
                    severity="low")
        
        # Successful upload after resize
        logger.info("File upload", category="user_actions",
                   user_id=user_id, action="upload_file",
                   metadata={"file_size": "8MB", "session_id": session_id})
        
        # User logs out
        logger.info("User logout", category="user_actions",
                   user_id=user_id, action="logout",
                   metadata={"session_duration": 1847, "session_id": session_id})
        
        # Verify journey was logged
        user_logs = logger.query(category="user_actions", user_id=user_id)
        assert len(user_logs) >= 7
    
    def test_system_maintenance_workflow(self, logger):
        """Simulate a system maintenance workflow."""
        maintenance_id = "maint_2026_01_19"
        
        logger.warning("Starting maintenance", category="system_events",
                      event_type="maintenance_start",
                      description=f"Scheduled maintenance {maintenance_id} beginning")
        
        logger.info("Database backup", category="system_events",
                   event_type="database_backup",
                   description="Creating pre-maintenance backup",
                   duration_ms=45000.0)
        
        logger.info("Index rebuild", category="system_events",
                   event_type="index_rebuild",
                   description="Rebuilding database indices",
                   duration_ms=120000.0)
        
        logger.info("Cache clear", category="system_events",
                   event_type="cache_clear",
                   description="Clearing application cache")
        
        logger.info("Maintenance complete", category="system_events",
                   event_type="maintenance_end",
                   description=f"Maintenance {maintenance_id} completed successfully",
                   duration_ms=165000.0)
        
        # Verify maintenance workflow
        results = logger.query(category="system_events", event_type="maintenance_start")
        assert len(results) >= 1
    
    def test_load_test_simulation(self, logger):
        """Simulate high load with multiple concurrent operations."""
        # Simulate burst of API requests
        for i in range(50):
            endpoint = f"/api/v1/items/{i % 10}"
            method = "GET"
            status = 200 if i % 10 != 0 else 503
            
            logger.info(f"Load test request {i}", category="api_requests",
                       endpoint=endpoint, method=method,
                       status_code=status,
                       response_time_ms=random.uniform(100.0, 2000.0))
        
        # Log performance warnings
        logger.warning("High load detected", category="system_events",
                      event_type="performance_warning",
                      description="Request queue length: 150, CPU: 85%, Memory: 78%")
        
        logger.warning("Database slow queries", category="system_events",
                      event_type="performance_warning",
                      description="5 queries exceeded 1000ms threshold",
                      duration_ms=1500.0)
        
        # Verify load test logged
        results = logger.query(category="api_requests")
        assert len(results) >= 50


class TestDiverseDataTypes:
    """Test with diverse data types and edge cases."""
    
    def test_various_json_structures(self, logger):
        """Log various JSON structures."""
        json_examples = [
            {"simple": "string", "number": 42, "boolean": True},
            {"nested": {"level1": {"level2": {"level3": "deep"}}}},
            {"array": [1, 2, 3, 4, 5]},
            {"mixed": [{"id": 1}, {"id": 2}]},
            {"empty_array": [], "null_value": None},
            {"unicode": "Hello 世界 🌍 مرحبا"},
            {"special_chars": "Test with 'quotes' and \"double quotes\""},
        ]
        
        for i, metadata in enumerate(json_examples):
            logger.info(f"JSON example {i}", category="user_actions",
                       user_id=f"json_test_{i}", action="test",
                       metadata=metadata)
        
        results = logger.query(category="user_actions")
        assert len(results) >= len(json_examples)
    
    def test_long_text_entries(self, logger):
        """Log entries with long text fields."""
        long_error = "A" * 5000
        long_stack = "\n".join([f"  File line_{i}, in function_{i}" for i in range(100)])
        
        logger.error("Long error message", category="errors",
                    error_code=500,
                    error_message=long_error,
                    stack_trace=long_stack,
                    severity="medium")
        
        results = logger.query(category="errors")
        assert len(results) >= 1
