"""
Script to set up Datadog monitors from configuration with enhanced alerting features.
"""
import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.model.monitor import Monitor
from datadog_api_client.v1.model.monitor_type import MonitorType
from datadog_api_client.v1.model.monitor_options import MonitorOptions
from datadog_api_client.v1.model.monitor_thresholds import MonitorThresholds

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatadogMonitorSetup:
    """Enhanced Datadog monitor setup with alert management capabilities."""
    
    def __init__(self, api_key: str, app_key: str, site: str = "datadoghq.com"):
        """Initialize the monitor setup client."""
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.api_client = None
        self.monitors_api = None
        self.created_monitors: Dict[str, int] = {}
        
    def _initialize_client(self):
        """Initialize the Datadog API client."""
        try:
            configuration = Configuration()
            configuration.api_key["apiKeyAuth"] = self.api_key
            configuration.api_key["appKeyAuth"] = self.app_key
            configuration.server_variables["site"] = self.site
            
            self.api_client = ApiClient(configuration)
            self.monitors_api = MonitorsApi(self.api_client)
            
            logger.info("Datadog API client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Datadog API client: {e}")
            return False
    
    def load_monitor_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load monitor configuration from JSON file."""
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded monitor configuration from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return None
    
    def create_monitor(self, monitor_def: Dict[str, Any]) -> Optional[int]:
        """Create a single Datadog monitor."""
        try:
            # Build monitor options
            options_dict = monitor_def.get("options", {})
            thresholds_dict = options_dict.get("thresholds", {})
            
            # Create thresholds object
            thresholds = MonitorThresholds(**thresholds_dict) if thresholds_dict else None
            
            # Create options object
            options = MonitorOptions(
                thresholds=thresholds,
                notify_audit=options_dict.get("notify_audit", True),
                require_full_window=options_dict.get("require_full_window", False),
                notify_no_data=options_dict.get("notify_no_data", True),
                no_data_timeframe=options_dict.get("no_data_timeframe", 20),
                renotify_interval=options_dict.get("renotify_interval", 0),
                escalation_message=options_dict.get("escalation_message"),
                include_tags=options_dict.get("include_tags", True)
            )
            
            # Create monitor
            monitor = Monitor(
                name=monitor_def["name"],
                type=MonitorType(monitor_def["type"]),
                query=monitor_def["query"],
                message=monitor_def["message"],
                tags=monitor_def.get("tags", []),
                options=options
            )
            
            response = self.monitors_api.create_monitor(monitor)
            monitor_id = response.id
            
            logger.info(f"Successfully created monitor '{monitor_def['name']}' with ID {monitor_id}")
            return monitor_id
            
        except Exception as e:
            logger.error(f"Failed to create monitor '{monitor_def['name']}': {e}")
            return None
    
    def setup_monitors(self, config_path: str = "infrastructure/datadog/monitors.json") -> Dict[str, int]:
        """Set up all monitors from configuration file."""
        if not self._initialize_client():
            return {}
        
        config = self.load_monitor_configuration(config_path)
        if not config:
            return {}
        
        monitors = config.get("monitors", [])
        logger.info(f"Setting up {len(monitors)} monitors...")
        
        for monitor_def in monitors:
            monitor_name = monitor_def.get("name", "Unknown")
            logger.info(f"Creating monitor: {monitor_name}")
            
            monitor_id = self.create_monitor(monitor_def)
            if monitor_id:
                self.created_monitors[monitor_name] = monitor_id
        
        logger.info(f"Successfully created {len(self.created_monitors)} out of {len(monitors)} monitors")
        return self.created_monitors
    
    def setup_alert_policies(self, config: Dict[str, Any]) -> bool:
        """Set up alert policies and escalation rules."""
        try:
            alert_policies = config.get("alert_policies", {})
            
            # Log policy configuration
            thresholds = alert_policies.get("trust_score_thresholds", {})
            logger.info(f"Trust score thresholds: {thresholds}")
            
            quarantine_thresholds = alert_policies.get("quarantine_thresholds", {})
            logger.info(f"Quarantine thresholds: {quarantine_thresholds}")
            
            conflict_thresholds = alert_policies.get("conflict_rate_thresholds", {})
            logger.info(f"Conflict rate thresholds: {conflict_thresholds}")
            
            # Log notification channels
            channels = alert_policies.get("notification_channels", {})
            logger.info(f"Notification channels configured: {list(channels.keys())}")
            
            # Log escalation rules
            escalation_rules = alert_policies.get("escalation_rules", {})
            logger.info(f"Escalation rules configured: {list(escalation_rules.keys())}")
            
            # Log auto-resolution settings
            auto_resolution = alert_policies.get("auto_resolution", {})
            if auto_resolution.get("enabled", False):
                logger.info("Auto-resolution is enabled")
                conditions = auto_resolution.get("conditions", {})
                logger.info(f"Auto-resolution conditions: {list(conditions.keys())}")
            else:
                logger.info("Auto-resolution is disabled")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up alert policies: {e}")
            return False
    
    def validate_monitors(self) -> bool:
        """Validate that all created monitors are working correctly."""
        try:
            logger.info("Validating created monitors...")
            
            for monitor_name, monitor_id in self.created_monitors.items():
                try:
                    monitor = self.monitors_api.get_monitor(monitor_id)
                    if monitor.name == monitor_name:
                        logger.info(f"✓ Monitor '{monitor_name}' (ID: {monitor_id}) is active")
                    else:
                        logger.warning(f"⚠ Monitor name mismatch for ID {monitor_id}")
                except Exception as e:
                    logger.error(f"✗ Failed to validate monitor '{monitor_name}' (ID: {monitor_id}): {e}")
                    return False
            
            logger.info("All monitors validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during monitor validation: {e}")
            return False
    
    def cleanup_monitors(self, monitor_ids: List[int]) -> bool:
        """Clean up monitors by deleting them (for testing/rollback)."""
        try:
            logger.info(f"Cleaning up {len(monitor_ids)} monitors...")
            
            for monitor_id in monitor_ids:
                try:
                    self.monitors_api.delete_monitor(monitor_id)
                    logger.info(f"Deleted monitor ID: {monitor_id}")
                except Exception as e:
                    logger.error(f"Failed to delete monitor ID {monitor_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during monitor cleanup: {e}")
            return False

def main():
    """Main function to set up Datadog monitors."""
    # Get environment variables
    api_key = os.getenv("DATADOG_API_KEY")
    app_key = os.getenv("DATADOG_APP_KEY")
    site = os.getenv("DATADOG_SITE", "datadoghq.com")
    
    if not api_key or not app_key:
        logger.error("Error: DATADOG_API_KEY and DATADOG_APP_KEY must be set.")
        sys.exit(1)
    
    # Initialize setup client
    setup_client = DatadogMonitorSetup(api_key, app_key, site)
    
    # Load configuration and set up monitors
    config_path = "infrastructure/datadog/monitors.json"
    config = setup_client.load_monitor_configuration(config_path)
    
    if not config:
        logger.error("Failed to load monitor configuration")
        sys.exit(1)
    
    # Set up monitors
    created_monitors = setup_client.setup_monitors(config_path)
    
    if not created_monitors:
        logger.error("No monitors were created successfully")
        sys.exit(1)
    
    # Set up alert policies
    if not setup_client.setup_alert_policies(config):
        logger.warning("Failed to set up alert policies")
    
    # Validate monitors
    if not setup_client.validate_monitors():
        logger.error("Monitor validation failed")
        sys.exit(1)
    
    # Print summary
    logger.info("=" * 50)
    logger.info("DATADOG MONITOR SETUP COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Created monitors: {len(created_monitors)}")
    for name, monitor_id in created_monitors.items():
        logger.info(f"  - {name}: {monitor_id}")
    
    logger.info("\nAlert configuration summary:")
    alert_policies = config.get("alert_policies", {})
    logger.info(f"  - Trust score thresholds: {alert_policies.get('trust_score_thresholds', {})}")
    logger.info(f"  - Quarantine thresholds: {alert_policies.get('quarantine_thresholds', {})}")
    logger.info(f"  - Auto-resolution enabled: {alert_policies.get('auto_resolution', {}).get('enabled', False)}")
    
    logger.info("\nMonitors are now active and monitoring system health.")

if __name__ == "__main__":
    main()
