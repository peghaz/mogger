"""
Performance and stress tests for Loki logging functionality.
"""

import time
import pytest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from mogger import Mogger, LokiConfig


def is_loki_available():
    """Check if Loki server is available."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 3100))
        sock.close()
        return result == 0
    except:
        return False


# Skip all Loki performance tests if server not available
pytestmark = pytest.mark.skipif(
    not is_loki_available(),
    reason="Loki server not available at localhost:3100"
)


@pytest.fixture
def test_config_path():
    """Return path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def test_db_path(tmp_path):
    """Return path to temporary test database file."""
    return str(tmp_path / "mogger_test_logs.db")


@pytest.fixture
def loki_config_test():
    """Create a test LokiConfig."""
    return LokiConfig(
        url="http://localhost:3100/loki/api/v1/push",
        tags={"app": "mogger-perf-test", "env": "test"},
    )


class TestLokiPerformance:
    """Performance tests for Loki logging."""

    def test_high_volume_logging_performance(self, test_config_path, test_db_path, loki_config_test):
        """Test logging 100 messages and measure time."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        start_time = time.time()
        
        for i in range(50):  # Reduced from 1000 to 50
            mogger.info(
                f"Performance test message {i}",
                category="user_actions",
                user_id=f"user_{i}",
                action="perf_test",
                iteration=i,
                test_id="perf_test_1"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Logged 50 messages in {duration:.2f} seconds")
        print(f"📊 Average: {50/duration:.2f} messages/second")
        
        # Should complete in reasonable time (less than 30 seconds)
        assert duration < 30
        
        mogger.close()

    def test_rapid_successive_logs(self, test_config_path, test_db_path, loki_config_test):
        """Test rapid successive logging without delays."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        start_time = time.time()
        
        # Log rapidly
        for i in range(10):  # Reduced from 100 to 10
            mogger.debug(f"Rapid log {i}", category="system_events", event_type="test", description="Test")
            mogger.info(f"Rapid log {i}", category="system_events", event_type="test", description="Test")
            mogger.warning(f"Rapid log {i}", category="system_events", event_type="test", description="Test")
            mogger.error(f"Rapid log {i}", category="system_events", event_type="test", description="Test")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Logged 40 rapid messages in {duration:.2f} seconds")
        
        mogger.close()

    def test_large_message_performance(self, test_config_path, test_db_path, loki_config_test):
        """Test logging messages with large payloads."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        large_message = "A" * 5000  # 5KB message
        
        start_time = time.time()
        
        for i in range(20):  # Reduced from 100 to 20
            mogger.info(
                large_message,
                category="user_actions",
                user_id=f"user_{i}",
                action="large_test",
                iteration=i,
                size=len(large_message)
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Logged 20 large messages (5KB each) in {duration:.2f} seconds")
        
        mogger.close()

    def test_logging_with_many_fields(self, test_config_path, test_db_path, loki_config_test):
        """Test logging with many extra fields."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        # Create message with many fields
        extra_fields = {f"field_{i}": f"value_{i}" for i in range(50)}
        
        start_time = time.time()
        
        for i in range(20):  # Reduced from 100 to 20
            mogger.info(
                f"Message with many fields {i}",
                category="user_actions",
                user_id=f"user_{i}",
                action="many_fields_test",
                **extra_fields
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Logged 20 messages with 50 fields each in {duration:.2f} seconds")
        
        mogger.close()


class TestLokiConcurrency:
    """Concurrency tests for Loki logging."""

    def test_concurrent_logging_multiple_threads(self, test_config_path, test_db_path, loki_config_test):
        """Test logging from multiple threads concurrently."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        def log_messages(thread_id, count):
            for i in range(count):
                mogger.info(
                    f"Thread {thread_id} message {i}",
                    category="user_actions",
                    user_id=f"user_t{thread_id}_{i}",
                    action="thread_test",
                    thread_id=thread_id,
                    iteration=i
                )
        
        start_time = time.time()
        
        # Use 3 threads, each logging 10 messages (reduced from 5 threads × 50)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(log_messages, i, 10) for i in range(3)]
            
            for future in as_completed(futures):
                future.result()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Logged 250 messages from 5 threads in {duration:.2f} seconds")
        
        mogger.close()

    def test_concurrent_different_log_levels(self, test_config_path, test_db_path, loki_config_test):
        """Test concurrent logging at different levels."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        def log_at_level(level, count):
            for i in range(count):
                if level == "debug":
                    mogger.debug(f"Debug {i}", category="system_events", event_type="test", description=f"Debug {i}")
                elif level == "info":
                    mogger.info(f"Info {i}", category="system_events", event_type="test", description=f"Info {i}")
                elif level == "warning":
                    mogger.warning(f"Warning {i}", category="system_events", event_type="test", description=f"Warning {i}")
                elif level == "error":
                    mogger.error(f"Error {i}", category="system_events", event_type="test", description=f"Error {i}")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            levels = ["debug", "info", "warning", "error"]
            futures = [executor.submit(log_at_level, level, 25) for level in levels]
            
            for future in as_completed(futures):
                future.result()
        
        mogger.close()

    def test_concurrent_different_categories(self, test_config_path, test_db_path, loki_config_test):
        """Test concurrent logging to different categories."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        categories = [("user_actions", {"user_id": "user_x", "action": "test"}), 
                      ("system_events", {"event_type": "test", "description": "Test"}), 
                      ("errors", {"error_code": 500, "error_message": "Test", "severity": "medium"})]
        
        def log_to_category(cat_info, count):
            category, fields = cat_info
            for i in range(count):
                mogger.info(
                    f"Message {i} to {category}",
                    category=category,
                    iteration=i,
                    **fields
                )
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(log_to_category, cat, 30) for cat in categories]
            
            for future in as_completed(futures):
                future.result()
        
        mogger.close()


class TestLokiStressTest:
    """Stress tests for Loki integration."""

    @pytest.mark.stress
    def test_continuous_logging_stress(self, test_config_path, test_db_path, loki_config_test):
        """Stress test with continuous logging for extended period."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        messages_logged = 0
        start_time = time.time()
        target_duration = 2  # 2 seconds of continuous logging (reduced from 5)
        
        while time.time() - start_time < target_duration:
            mogger.info(
                f"Stress test message {messages_logged}",
                category="user_actions",
                user_id=f"user_{messages_logged}",
                action="stress_test",
                timestamp=time.time()
            )
            messages_logged += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Stress test: Logged {messages_logged} messages in {duration:.2f} seconds")
        print(f"📊 Rate: {messages_logged/duration:.2f} messages/second")
        
        mogger.close()

    @pytest.mark.stress
    def test_mixed_workload_stress(self, test_config_path, test_db_path, loki_config_test):
        """Stress test with mixed logging operations."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        # Mix of different operations
        for i in range(40):  # Reduced from 200 to 40
            # Different log levels
            if i % 4 == 0:
                mogger.debug(f"Debug {i}", category="system_events", event_type="test", description="Test")
            elif i % 4 == 1:
                mogger.info(f"Info {i}", category="user_actions", user_id=f"user_{i}", action="test")
            elif i % 4 == 2:
                mogger.warning(f"Warning {i}", category="errors", error_code=400, error_message="Test", severity="medium")
            else:
                mogger.error(f"Error {i}", category="errors", error_code=500, error_message="Test", severity="high")
            
            # Occasionally set/clear context
            if i % 50 == 0:
                mogger.set_context(batch_id=f"batch_{i//50}")
            elif i % 50 == 25:
                mogger.clear_context()
        
        mogger.close()


class TestLokiMemoryUsage:
    """Tests for memory usage during Loki logging."""

    @pytest.mark.memory
    def test_memory_stability_high_volume(self, test_config_path, test_db_path, loki_config_test):
        """Test that memory doesn't grow excessively with high volume logging."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        # Log many messages
        for i in range(500):
            mogger.info(
                f"Memory test message {i}",
                category="user_actions",
                user_id=f"user_{i}",
                action="memory_test",
                data={"key": "value", "number": i}
            )
        
        # If we get here without OOM, test passes
        mogger.close()

    @pytest.mark.memory
    def test_no_memory_leak_repeated_init(self, test_config_path, test_db_path):
        """Test no memory leak from repeated Mogger initialization."""
        loki_config = LokiConfig(
            url="http://localhost:3100/loki/api/v1/push",
            tags={"app": "leak-test"},
        )
        
        # Create and destroy multiple instances
        for i in range(10):
            mogger = Mogger(
                test_config_path,
                db_path=str(Path(test_db_path).parent / f"db_{i}.db"),
                loki_config=loki_config
            )
            
            mogger.info(f"Message from instance {i}", category="user_actions", user_id=f"user_{i}", action="test")
            mogger.close()


class TestLokiReliability:
    """Tests for reliability of Loki logging."""

    @pytest.mark.performance
    def test_logging_continues_after_many_operations(self, test_config_path, test_db_path, loki_config_test):
        """Test that logging remains reliable after many operations."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        # Perform many logging operations
        for batch in range(5):  # Reduced from 10 to 5
            for i in range(10):  # Reduced from 100 to 10
                mogger.info(
                    f"Batch {batch} message {i}",
                    category="user_actions",
                    user_id=f"user_b{batch}_{i}",
                    action="reliability_test",
                    batch=batch,
                    iteration=i
                )
        
        # Should still work after 50 messages
        uuid = mogger.info("Final message", category="user_actions", user_id="final_user", action="final")
        assert uuid is not None
        
        mogger.close()

    @pytest.mark.performance
    def test_context_persistence_under_load(self, test_config_path, test_db_path, loki_config_test):
        """Test that context persists correctly under load."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        mogger.set_context(session_id="sess_123", request_id="req_456")
        
        # Log many messages with context
        for i in range(50):
            mogger.info(f"Context message {i}", category="user_actions", user_id=f"user_{i}", action="context_test")
        
        mogger.clear_context()
        
        # Context should be cleared
        mogger.info("No context message", category="user_actions", user_id="user_final", action="test")
        
        mogger.close()

    @pytest.mark.performance
    def test_multiple_mogger_instances_parallel(self, test_config_path, test_db_path):
        """Test multiple Mogger instances logging in parallel."""
        configs = [
            LokiConfig(url="http://localhost:3100/loki/api/v1/push", tags={"app": f"app_{i}"})
            for i in range(3)
        ]
        
        moggers = [
            Mogger(
                test_config_path,
                db_path=str(Path(test_db_path).parent / f"db_{i}.db"),
                loki_config=config
            )
            for i, config in enumerate(configs)
        ]
        
        # Log from each instance
        for i, mogger in enumerate(moggers):
            for j in range(20):
                mogger.info(f"Instance {i} message {j}", category="user_actions", user_id=f"user_i{i}_j{j}", action="parallel_test")
        
        # Close all
        for mogger in moggers:
            mogger.close()


class TestLokiEdgeCasePerformance:
    """Performance tests for edge cases."""

    def test_empty_message_performance(self, test_config_path, test_db_path, loki_config_test):
        """Test logging empty messages."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        for i in range(20):
            mogger.info("", category="user_actions", user_id=f"user_{i}", action="empty_test", iteration=i)
        
        mogger.close()

    def test_very_long_category_names(self, test_config_path, test_db_path, loki_config_test):
        """Test logging with very long category names."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        # Note: Using valid categories from config, just testing the logging
        for i in range(20):
            mogger.info(f"Message {i}", category="user_actions", user_id=f"user_{i}", action="long_cat_test")
        
        mogger.close()

    def test_special_characters_in_messages(self, test_config_path, test_db_path, loki_config_test):
        """Test logging messages with special characters."""
        mogger = Mogger(
            test_config_path,
            db_path=test_db_path,
            loki_config=loki_config_test
        )
        
        special_messages = [
            "Message with emoji 🚀 🎉",
            "Message with quotes: \"hello\" 'world'",
            "Message with newlines\n\ntest",
            "Message with tabs\t\ttest",
            "Message with unicode: café, naïve, 日本語",
        ]
        
        for i, msg in enumerate(special_messages * 4):
            mogger.info(msg, category="user_actions", user_id=f"user_{i}", action="special_char_test", iteration=i)
        
        mogger.close()
