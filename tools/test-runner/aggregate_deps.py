#!/usr/bin/env python3
"""
Dependency Aggregation Script for Test Runner

Dynamically aggregates dependencies from all service requirements.txt files
and ensures the test runner environment has all necessary packages.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set
import re


class DependencyAggregator:
    def __init__(self, project_root: Path = None):
        """Initialize with project root directory"""
        if project_root is None:
            # Assume we're in tools/test-runner/
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = project_root
        self.services_dir = project_root / "services"
        
    def parse_requirements_file(self, req_file: Path) -> Dict[str, str]:
        """Parse a requirements.txt file and return package:version dict"""
        requirements = {}
        
        if not req_file.exists():
            return requirements
            
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                    
                # Parse package==version format
                if '==' in line:
                    package, version = line.split('==', 1)
                    # Handle extras like uvicorn[standard] - keep the extras for UV
                    requirements[package.strip()] = f"=={version.strip()}"
                elif '>=' in line:
                    package, version = line.split('>=', 1)
                    package = package.split('[')[0]
                    requirements[package.strip()] = f">={version.strip()}"
                else:
                    # Handle packages without version specifiers
                    package = line.split('[')[0]
                    requirements[package.strip()] = ""
                    
        return requirements
    
    def aggregate_all_dependencies(self) -> Dict[str, str]:
        """Aggregate dependencies from all services"""
        all_deps = {}
        conflicts = []
        
        print(f"Scanning services in: {self.services_dir}")
        
        # Find all service directories
        for service_dir in self.services_dir.iterdir():
            if not service_dir.is_dir():
                continue
                
            req_file = service_dir / "requirements.txt"
            if not req_file.exists():
                print(f"  ⚠️  No requirements.txt found in {service_dir.name}")
                continue
                
            print(f"  📦 Processing {service_dir.name}/requirements.txt")
            service_deps = self.parse_requirements_file(req_file)
            
            # Merge dependencies, checking for conflicts
            for package, version in service_deps.items():
                if package in all_deps:
                    if all_deps[package] != version and version != "":
                        # Version conflict - use the more restrictive one
                        existing = all_deps[package]
                        if self._is_more_restrictive(version, existing):
                            conflicts.append(f"{package}: {existing} -> {version}")
                            all_deps[package] = version
                        else:
                            conflicts.append(f"{package}: keeping {existing} over {version}")
                else:
                    all_deps[package] = version
        
        # Report conflicts
        if conflicts:
            print("\n⚠️  Version conflicts resolved:")
            for conflict in conflicts:
                print(f"    {conflict}")
        
        return all_deps
    
    def _is_more_restrictive(self, version1: str, version2: str) -> bool:
        """Simple heuristic to determine which version is more restrictive"""
        # Prefer exact versions (==) over ranges (>=)
        if version1.startswith('>=') and not version2.startswith('>='):
            return False
        if not version1.startswith('>=') and version2.startswith('>='):
            return True
        return False
    
    def install_dependencies(self, dependencies: Dict[str, str]) -> bool:
        """Install aggregated dependencies using UV"""
        if not dependencies:
            print("No dependencies to install")
            return True
            
        print(f"\n🔧 Installing {len(dependencies)} packages...")
        
        # Build UV add command
        packages = []
        for package, version in dependencies.items():
            if version and version != "":
                if version.startswith('>=') or version.startswith('=='):
                    packages.append(f"{package}{version}")
                else:
                    # Assume it's a version number without operator
                    packages.append(f"{package}=={version}")
            else:
                packages.append(package)
        
        # Split into chunks to avoid command line length limits
        chunk_size = 20
        for i in range(0, len(packages), chunk_size):
            chunk = packages[i:i + chunk_size]
            cmd = ["uv", "add"] + chunk
            
            print(f"  Running: uv add {' '.join(chunk[:3])}{'...' if len(chunk) > 3 else ''}")
            
            try:
                result = subprocess.run(
                    cmd, 
                    cwd=Path(__file__).parent,
                    capture_output=True, 
                    text=True,
                    timeout=300  # 5 minute timeout per chunk
                )
                
                if result.returncode != 0:
                    print(f"❌ Failed to install chunk: {result.stderr}")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("❌ Installation timed out")
                return False
            except Exception as e:
                print(f"❌ Installation error: {e}")
                return False
        
        print("✅ All dependencies installed successfully")
        return True
    
    def run(self, install: bool = True) -> bool:
        """Main execution method"""
        print("🚀 Aggregating dependencies from all services...\n")
        
        # Aggregate all dependencies
        all_deps = self.aggregate_all_dependencies()
        
        if not all_deps:
            print("❌ No dependencies found")
            return False
        
        print(f"\n📋 Found {len(all_deps)} unique packages:")
        for package, version in sorted(all_deps.items()):
            print(f"  {package}{version}")
        
        # Install if requested
        if install:
            return self.install_dependencies(all_deps)
        
        return True


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate service dependencies for test runner")
    parser.add_argument("--no-install", action="store_true", help="Only list dependencies, don't install")
    parser.add_argument("--project-root", type=Path, help="Project root directory")
    
    args = parser.parse_args()
    
    aggregator = DependencyAggregator(args.project_root)
    success = aggregator.run(install=not args.no_install)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()