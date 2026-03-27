#!/usr/bin/env python3
"""
Demo script for the CLI dashboard that works without external dependencies.
"""
import sys
import time
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.logging_config import setup_logging
from src.prediction_engine.cli_dashboard import CLIDashboard, DashboardMetrics
from datetime import datetime, timedelta

def create_mock_metrics() -> DashboardMetrics:
    """Create mock metrics for demonstration."""
    return DashboardMetrics(
        timestamp=datetime.now(),
        total_agents=8,
        active_agents=6,
        quarantined_agents=2,
        system_running=True,
        recent_conflicts=[],
        recent_interventions=[],
        resource_utilization={
            "cpu": 0.75,
            "memory": 0.60,
            "network": 0.45,
            "storage": 0.30,
            "database": 0.85
        },
        trust_scores={
            "agent_001": 85,
            "agent_002": 92,
            "agent_003": 25,  # Low trust score
            "agent_004": 78,
            "agent_005": 88,
            "agent_006": 15   # Very low trust score
        },
        current_risk_score=0.65,  # Moderate risk
        gemini_api_status=True
    )

def main():
    """Run a demo of the CLI dashboard."""
    # Set up logging
    logger = setup_logging(level="INFO")
    
    print("=" * 60)
    print("CHORUS CLI DASHBOARD DEMO")
    print("=" * 60)
    print("This demo shows the CLI dashboard interface.")
    print("Press Ctrl+C to exit.")
    print("=" * 60)
    print()
    
    # Create dashboard instance
    dashboard = CLIDashboard()
    
    # Override the metrics collection to use mock data
    dashboard.current_metrics = create_mock_metrics()
    
    try:
        # Clear screen and show dashboard
        dashboard._clear_screen()
        dashboard._hide_cursor()
        
        # Display the dashboard content once
        content = dashboard._build_display_content()
        print(content)
        
        # Show cursor again
        dashboard._show_cursor()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("The actual dashboard would update in real-time.")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        logger.exception(f"Error in demo: {e}")
    finally:
        dashboard._show_cursor()

if __name__ == "__main__":
    main()