
import pytest
from unittest.mock import MagicMock
import os
import yaml

class TestPropertyDeploymentSecurity:
    """
    Property 2: Deployment configuration security.
    Validates: Requirements 2.3, 2.4
    """

    def test_no_hardcoded_secrets_in_dockerfile(self):
        """Verify Dockerfile does not contain hardcoded secrets."""
        with open("backend/Dockerfile.cloudrun", "r") as f:
            content = f.read()
            
        forbidden_terms = ["API_KEY", "PASSWORD", "SECRET", "TOKEN"]
        for line in content.splitlines():
            # Skip comments
            if line.strip().startswith("#"):
                continue
                
            for term in forbidden_terms:
                if term in line and "ENV" in line and "=" in line:
                    # Allow referencing env vars (e.g. ENV KEY=$KEY) but not setting values
                    parts = line.split("=")
                    if len(parts) > 1 and not parts[1].strip().startswith("$"):
                        pytest.fail(f"Potential hardcoded secret found in Dockerfile: {line}")

    def test_firebase_security_headers(self):
        """Verify Firebase configuration includes security headers."""
        with open("frontend/firebase.json", "r") as f:
            config = yaml.safe_load(f) # JSON is valid YAML
            
        headers = config.get("hosting", {}).get("headers", [])
        assert len(headers) > 0, "No security headers configured in firebase.json"
        
        # Check for CORS header as an example of explicit configuration
        cors_found = False
        for header_group in headers:
            for header in header_group.get("headers", []):
                if header["key"] == "Access-Control-Allow-Origin":
                    cors_found = True
                    break
        
        assert cors_found, "CORS headers not configured in firebase.json"

    def test_cloudbuild_secure_env_vars(self):
        """Verify Cloud Build config uses substitution variables for sensitive data."""
        with open("cloudbuild.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        steps = config.get("steps", [])
        for step in steps:
            args = step.get("args", [])
            # Check for hardcoded project IDs or secrets in args
            for arg in args:
                if "gcr.io/" in arg and "$PROJECT_ID" not in arg:
                     # This is a heuristic, might need adjustment for specific hardcoded public images
                     if "cloud-builders" not in arg and "google.com" not in arg:
                        pytest.fail(f"Hardcoded image path found in Cloud Build: {arg}. Use $PROJECT_ID.")
