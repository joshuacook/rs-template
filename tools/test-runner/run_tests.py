#!/usr/bin/env python3
"""
Integration Test Runner
Orchestrates integration tests across all services
"""
import os
import sys
import argparse
import subprocess
import json
from typing import List, Dict, Any
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our dependency aggregator
from aggregate_deps import DependencyAggregator

class TestRunner:
    def __init__(self, environment: str = "local", verbose: bool = False, update_deps: bool = False):
        self.environment = environment
        self.verbose = verbose
        self.update_deps = update_deps
        self.project_id = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
        # Try multiple token env var formats
        self.test_token = (
            os.getenv("TEST_BYPASS_TOKEN") or 
            os.getenv(f"TEST_BYPASS_TOKEN_{self.project_id.upper().replace('-', '_')}") or
            ""
        )
        
        # Set base URLs based on environment
        if environment == "local":
            self.base_url = "http://localhost:8080"
        elif environment == "staging":
            # Use custom domain for staging
            self.base_url = f"https://{self.project_id}.staging.radicalsymmetry.com"
        elif environment == "production":
            # Use custom domain for production
            self.base_url = f"https://{self.project_id}.production.radicalsymmetry.com"
        else:
            raise ValueError(f"Unknown environment: {environment}")
        
        self.headers = {
            "Authorization": f"Bearer {self.test_token}",
            "Content-Type": "application/json"
        }
        
        # Test results
        self.results: Dict[str, List[Dict[str, Any]]] = {
            "passed": [],
            "failed": [],
            "skipped": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with level"""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {message}")
    
    def check_service_health(self) -> bool:
        """Check if services are healthy"""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    self.log(f"Gateway service is healthy: {response.json()}")
                    return True
                else:
                    self.log(f"Gateway health check failed: {response.status_code}", "ERROR")
                    return False
        except Exception as e:
            self.log(f"Cannot connect to gateway: {e}", "ERROR")
            return False
    
    def run_service_tests(self, service: str) -> bool:
        """Run integration tests for a specific service"""
        self.log(f"\n{'='*50}")
        self.log(f"Running {service} integration tests")
        self.log(f"{'='*50}")
        
        # Build test directory path
        test_dir = Path(__file__).parent.parent.parent / "services" / service / "tests" / "integration"
        
        if not test_dir.exists():
            self.log(f"No integration tests found for {service}", "WARNING")
            self.results["skipped"].append({
                "service": service,
                "reason": "No integration tests found"
            })
            return True
        
        # Set environment variables for tests
        env = os.environ.copy()
        env["TEST_BASE_URL"] = self.base_url
        env["TEST_TOKEN"] = self.test_token
        env["TEST_ENVIRONMENT"] = self.environment
        
        # Add service directory to Python path so imports work
        service_dir = test_dir.parent.parent
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{service_dir}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(service_dir)
        
        # Run pytest using UV (as per TESTING_PLAYBOOK)
        cmd = [
            "uv", "run", "pytest",
            str(test_dir),
            "-v" if self.verbose else "-q",
            "--tb=short",
            "--color=yes"
        ]
        
        try:
            # Run from test-runner directory so UV uses our unified environment
            test_runner_dir = Path(__file__).parent
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                cwd=str(test_runner_dir)
            )
            
            if result.returncode == 0:
                self.log(f"✅ {service} tests passed", "INFO")
                self.results["passed"].append({
                    "service": service,
                    "output": result.stdout if self.verbose else "Tests passed"
                })
                return True
            else:
                self.log(f"❌ {service} tests failed", "ERROR")
                self.log(result.stdout, "ERROR")
                self.log(result.stderr, "ERROR")
                self.results["failed"].append({
                    "service": service,
                    "output": result.stdout,
                    "error": result.stderr
                })
                return False
                
        except Exception as e:
            self.log(f"Error running {service} tests: {e}", "ERROR")
            self.results["failed"].append({
                "service": service,
                "error": str(e)
            })
            return False
    
    def ensure_dependencies(self) -> bool:
        """Ensure all service dependencies are installed in test runner environment"""
        try:
            self.log("🔧 Checking and updating dependencies...")
            aggregator = DependencyAggregator()
            
            # For now, we'll be conservative and only install if user explicitly requests
            # In the future, we could add auto-detection of missing dependencies
            success = aggregator.run(install=True)
            
            if success:
                self.log("✅ Dependencies are up to date")
            else:
                self.log("❌ Failed to update dependencies", "ERROR")
            
            return success
            
        except Exception as e:
            self.log(f"❌ Error updating dependencies: {e}", "ERROR")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        self.log(f"\n🚀 Starting integration tests for environment: {self.environment}")
        self.log(f"Base URL: {self.base_url}")
        
        # Update dependencies if requested
        if self.update_deps:
            if not self.ensure_dependencies():
                self.log("❌ Dependency update failed, continuing with existing environment...")
        
        # Check service health first
        if not self.check_service_health():
            self.log("Services are not healthy. Aborting tests.", "ERROR")
            return False
        
        # Run tests for each service
        services = ["gateway", "api", "ai"]
        all_passed = True
        
        for service in services:
            if not self.run_service_tests(service):
                all_passed = False
        
        # Print summary
        self.print_summary()
        
        return all_passed
    
    def print_summary(self):
        """Print test results summary"""
        self.log(f"\n{'='*50}")
        self.log("TEST SUMMARY")
        self.log(f"{'='*50}")
        
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["skipped"])
        
        self.log(f"Total: {total} services tested")
        self.log(f"✅ Passed: {len(self.results['passed'])}")
        self.log(f"❌ Failed: {len(self.results['failed'])}")
        self.log(f"⏭️  Skipped: {len(self.results['skipped'])}")
        
        if self.results["failed"]:
            self.log("\nFailed services:", "ERROR")
            for result in self.results["failed"]:
                self.log(f"  - {result['service']}", "ERROR")
        
        if self.results["skipped"]:
            self.log("\nSkipped services:", "WARNING")
            for result in self.results["skipped"]:
                self.log(f"  - {result['service']}: {result['reason']}", "WARNING")

def main():
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument(
        "environment",
        choices=["local", "staging", "production"],
        help="Environment to test against"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-s", "--service",
        choices=["gateway", "api", "ai"],
        help="Run tests for specific service only"
    )
    parser.add_argument(
        "--update-deps",
        action="store_true",
        help="Update dependencies from all services before running tests"
    )
    
    args = parser.parse_args()
    
    # Check for test token
    project_id = os.getenv("GCP_PROJECT_ID", "PROJECT_NAME")
    test_token = (
        os.getenv("TEST_BYPASS_TOKEN") or 
        os.getenv(f"TEST_BYPASS_TOKEN_{project_id.upper().replace('-', '_')}")
    )
    if not test_token:
        print(f"ERROR: TEST_BYPASS_TOKEN not set in environment")
        print("Please set the test bypass token in your .env file or environment")
        sys.exit(1)
    
    # Run tests
    runner = TestRunner(args.environment, args.verbose, args.update_deps)
    
    if args.service:
        # Run specific service tests
        success = runner.run_service_tests(args.service)
    else:
        # Run all tests
        success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()