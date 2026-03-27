#!/usr/bin/env python3
"""
CLI Dashboard entry point for the Chorus Agent Conflict Predictor.

This script provides a command-line interface for monitoring the agent
conflict prediction system in real-time.
"""
import argparse
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.logging_config import setup_logging
from src.prediction_engine.cli_dashboard import dashboard_manager
from src.config import settings

def main():
    """Main entry point for the CLI dashboard."""
    parser = argparse.ArgumentParser(
        description="Chorus Agent Conflict Predictor - CLI Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_dashboard.py                    # Start with default settings
  python cli_dashboard.py --agents 7        # Start with 7 agents
  python cli_dashboard.py --log-level DEBUG # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--agents",
        type=int,
        metavar="N",
        help=f"Number of agents to create ({settings.agent_simulation.min_agents}-{settings.agent_simulation.max_agents})"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=settings.log_level,
        help="Set logging level (default: %(default)s)"
    )
    
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Dashboard refresh interval in seconds (default: %(default)s)"
    )
    
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear screen on startup (useful for debugging)"
    )
    
    args = parser.parse_args()
    
    # Validate agent count
    if args.agents is not None:
        if args.agents < settings.agent_simulation.min_agents or args.agents > settings.agent_simulation.max_agents:
            print(f"Error: Agent count must be between {settings.agent_simulation.min_agents} and {settings.agent_simulation.max_agents}")
            sys.exit(1)
    
    # Set up logging
    logger = setup_logging(level=args.log_level)
    
    # Configure dashboard refresh interval
    if hasattr(dashboard_manager.dashboard, 'refresh_interval'):
        dashboard_manager.dashboard.refresh_interval = args.refresh_interval
    
    # Print startup information
    if not args.no_clear:
        os.system('clear' if os.name == 'posix' else 'cls')
    
    print("=" * 60)
    print("CHORUS AGENT CONFLICT PREDICTOR")
    print("=" * 60)
    print(f"Agent Count: {args.agents or 'Random (5-10)'}")
    print(f"Log Level: {args.log_level}")
    print(f"Refresh Interval: {args.refresh_interval}s")
    print(f"Conflict Risk Threshold: {settings.conflict_prediction.risk_threshold}")
    print(f"Trust Score Threshold: {settings.trust_scoring.quarantine_threshold}")
    print("=" * 60)
    print()
    
    try:
        # Check environment variables
        if not settings.gemini.api_key:
            print("Warning: GEMINI_API_KEY not set. Conflict prediction will be limited.")
        
        # Run the dashboard
        dashboard_manager.run_interactive(agent_count=args.agents)
        
    except KeyboardInterrupt:
        print("\nGracefully shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()