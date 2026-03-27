"""
Main application entry point for the Chorus Agent Conflict Predictor.
"""
import sys
import argparse
from typing import Optional

from .config import Settings, load_settings
from .system_lifecycle import SystemLifecycleManager
from .logging_config import setup_logging, get_agent_logger
from .config_validator import validate_config_cli


def setup_application_logging(settings: Settings) -> None:
    """
    Setup application logging based on settings.
    
    Args:
        settings: Application settings
    """
    setup_logging(
        level=settings.logging.level.value,
        use_structured=settings.logging.structured
    )


def run_simulation_mode(settings: Settings) -> int:
    """
    Run the system in simulation mode.
    
    Args:
        settings: Application settings
        
    Returns:
        Exit code
    """
    from .prediction_engine.simulator import AgentNetwork
    from .prediction_engine.cli_dashboard import CLIDashboard
    
    agent_logger = get_agent_logger(__name__)
    
    # Create lifecycle manager
    lifecycle_manager = SystemLifecycleManager(settings)
    
    try:
        # Startup system
        if not lifecycle_manager.startup():
            agent_logger.log_agent_action(
                "ERROR",
                "System startup failed",
                action_type="simulation_startup_failed"
            )
            return 1
        
        # Initialize simulation components
        agent_network = AgentNetwork(
            min_agents=settings.agent_simulation.min_agents,
            max_agents=settings.agent_simulation.max_agents
        )
        
        cli_dashboard = CLIDashboard(refresh_rate=settings.cli_refresh_rate)
        
        # Register shutdown callbacks
        lifecycle_manager.register_shutdown_callback(agent_network.stop_simulation)
        lifecycle_manager.register_shutdown_callback(cli_dashboard.stop)
        
        agent_logger.log_agent_action(
            "INFO",
            "Starting agent simulation",
            action_type="simulation_start",
            context={
                "min_agents": settings.agent_simulation.min_agents,
                "max_agents": settings.agent_simulation.max_agents
            }
        )
        
        # Start simulation
        agent_network.start_simulation()
        cli_dashboard.start()
        
        # Wait for shutdown
        lifecycle_manager.wait_for_shutdown()
        
        return 0
        
    except KeyboardInterrupt:
        agent_logger.log_agent_action(
            "INFO",
            "Received keyboard interrupt, shutting down",
            action_type="keyboard_interrupt"
        )
        return 0
        
    except Exception as e:
        agent_logger.log_system_error(
            e,
            component="main",
            operation="run_simulation"
        )
        return 1
        
    finally:
        lifecycle_manager.shutdown()


def run_api_mode(settings: Settings) -> int:
    """
    Run the system in API mode.
    
    Args:
        settings: Application settings
        
    Returns:
        Exit code
    """
    try:
        import uvicorn
        from fastapi import FastAPI
        from .api.main import create_app
        
        agent_logger = get_agent_logger(__name__)
        
        # Create lifecycle manager
        lifecycle_manager = SystemLifecycleManager(settings)
        
        # Startup system
        if not lifecycle_manager.startup():
            agent_logger.log_agent_action(
                "ERROR",
                "System startup failed",
                action_type="api_startup_failed"
            )
            return 1
        
        # Create FastAPI app with lifecycle
        app = create_app(lifecycle_manager)
        
        agent_logger.log_agent_action(
            "INFO",
            "Starting API server",
            action_type="api_server_start",
            context={
                "host": settings.api_host,
                "port": settings.api_port,
                "workers": settings.api_workers
            }
        )
        
        # Run the server
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            workers=settings.api_workers,
            log_level=settings.logging.level.value.lower()
        )
        
        return 0
        
    except ImportError:
        print("FastAPI and uvicorn are required for API mode. Install with: pip install fastapi uvicorn")
        return 1
        
    except Exception as e:
        agent_logger = get_agent_logger(__name__)
        agent_logger.log_system_error(
            e,
            component="main",
            operation="run_api"
        )
        return 1


def run_health_check(settings: Settings) -> int:
    """
    Run health check and exit.
    
    Args:
        settings: Application settings
        
    Returns:
        Exit code
    """
    from .system_health import health_monitor
    
    try:
        # Run health checks
        results = health_monitor.force_health_check()
        
        print("Health Check Results:")
        all_passed = True
        
        for check_name, result in results.items():
            status_symbol = "✓" if result else "✗"
            status_text = "PASS" if result else "FAIL"
            print(f"  {status_symbol} {check_name}: {status_text}")
            
            if not result:
                all_passed = False
        
        if all_passed:
            print("\nAll health checks passed!")
            return 0
        else:
            print("\nSome health checks failed!")
            return 1
            
    except Exception as e:
        print(f"Health check failed with error: {str(e)}")
        return 1


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="Chorus Agent Conflict Predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s simulation                    # Run agent simulation with CLI dashboard
  %(prog)s api                          # Run REST API server
  %(prog)s validate-config              # Validate configuration
  %(prog)s health-check                 # Run health checks
  %(prog)s --env-file .env.prod api     # Run API with custom config file
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["simulation", "api", "validate-config", "health-check"],
        help="Application mode to run"
    )
    
    parser.add_argument(
        "--env-file",
        help="Path to .env file (default: .env)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level"
    )
    
    args = parser.parse_args()
    
    try:
        # Load settings
        if args.env_file:
            settings = load_settings(args.env_file)
            print(f"Loaded configuration from: {args.env_file}")
        else:
            settings = load_settings()
        
        # Override settings from command line
        if args.debug:
            settings.debug = True
        
        if args.log_level:
            settings.logging.level = args.log_level
        
        # Setup logging
        setup_application_logging(settings)
        
        # Run the appropriate mode
        if args.mode == "simulation":
            return run_simulation_mode(settings)
        
        elif args.mode == "api":
            return run_api_mode(settings)
        
        elif args.mode == "validate-config":
            return validate_config_cli(args.env_file)
        
        elif args.mode == "health-check":
            return run_health_check(settings)
        
        else:
            print(f"Unknown mode: {args.mode}")
            return 1
    
    except Exception as e:
        print(f"Application failed to start: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())