#!/usr/bin/env python3
"""
CI Setup Validation Script

Validates the CI/CD configuration and ensures all components are properly configured
for the session-notes FastMCP 2.0 project.
"""

import subprocess
import sys
from pathlib import Path

import yaml


class CIValidator:
    """Validates CI/CD setup for session-notes project."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.github_dir = project_root / ".github"
        self.workflows_dir = self.github_dir / "workflows"
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        """Record an error."""
        self.errors.append(f"❌ ERROR: {message}")

    def warning(self, message: str) -> None:
        """Record a warning."""
        self.warnings.append(f"⚠️  WARNING: {message}")

    def success(self, message: str) -> None:
        """Print success message."""
        print(f"✅ {message}")

    def validate_directory_structure(self) -> None:
        """Validate that all required directories and files exist."""
        print("🔍 Validating directory structure...")

        required_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/security-audit.yml",
            ".github/workflows/performance.yml",
            ".github/ci-config.yml",
            ".github/CI-README.md",
            ".pre-commit-config.yaml",
            "pyproject.toml",
            "pixi.lock",
        ]

        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.error(f"Missing required file: {file_path}")
            else:
                self.success(f"Found {file_path}")

    def validate_workflow_syntax(self) -> None:
        """Validate GitHub Actions workflow YAML syntax."""
        print("\n🔍 Validating workflow syntax...")

        workflow_files = ["ci.yml", "security-audit.yml", "performance.yml"]

        for workflow_file in workflow_files:
            workflow_path = self.workflows_dir / workflow_file
            if workflow_path.exists():
                try:
                    with open(workflow_path) as f:
                        yaml.safe_load(f)
                    self.success(f"Valid YAML syntax: {workflow_file}")
                except yaml.YAMLError as e:
                    self.error(f"Invalid YAML syntax in {workflow_file}: {e}")
            else:
                self.error(f"Workflow file not found: {workflow_file}")

    def validate_ci_config(self) -> None:
        """Validate CI configuration file."""
        print("\n🔍 Validating CI configuration...")

        config_path = self.github_dir / "ci-config.yml"
        if not config_path.exists():
            self.error("CI configuration file not found")
            return

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Validate required sections
            required_sections = [
                "project",
                "dependencies",
                "quality",
                "security",
                "performance",
                "fastmcp",
            ]

            for section in required_sections:
                if section not in config:
                    self.error(f"Missing required section in ci-config.yml: {section}")
                else:
                    self.success(f"Found CI config section: {section}")

            # Validate performance thresholds
            if "performance" in config and "thresholds" in config["performance"]:
                thresholds = config["performance"]["thresholds"]
                required_thresholds = [
                    "import_time_ms",
                    "startup_time_ms",
                    "memory_usage_mb",
                ]

                for threshold in required_thresholds:
                    if threshold not in thresholds:
                        self.warning(f"Missing performance threshold: {threshold}")
                    else:
                        self.success(f"Found performance threshold: {threshold}")

        except yaml.YAMLError as e:
            self.error(f"Invalid YAML in ci-config.yml: {e}")

    def validate_pixi_configuration(self) -> None:
        """Validate PIXI configuration for CI compatibility."""
        print("\n🔍 Validating PIXI configuration...")

        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            self.error("pyproject.toml not found")
            return

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                self.warning("Cannot validate TOML - install tomli/tomllib")
                return

        try:
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            # Check for required PIXI sections
            required_sections = [
                "tool.pixi.project",
                "tool.pixi.dependencies",
                "tool.pixi.environments",
                "tool.pixi.tasks",
            ]

            for section_path in required_sections:
                current = config
                for key in section_path.split("."):
                    if key in current:
                        current = current[key]
                    else:
                        self.error(f"Missing PIXI section: {section_path}")
                        break
                else:
                    self.success(f"Found PIXI section: {section_path}")

            # Validate CI-required environments
            if (
                "tool" in config
                and "pixi" in config["tool"]
                and "environments" in config["tool"]["pixi"]
            ):
                environments = config["tool"]["pixi"]["environments"]
                required_envs = ["quality", "quality-extended", "ci"]

                for env in required_envs:
                    if env not in environments:
                        self.error(f"Missing required PIXI environment: {env}")
                    else:
                        self.success(f"Found PIXI environment: {env}")

            # Validate CI-required tasks
            if (
                "tool" in config
                and "pixi" in config["tool"]
                and "tasks" in config["tool"]["pixi"]
            ):
                tasks = config["tool"]["pixi"]["tasks"]
                required_tasks = ["test", "lint", "typecheck", "quality", "ci-test"]

                for task in required_tasks:
                    if task not in tasks:
                        self.error(f"Missing required PIXI task: {task}")
                    else:
                        self.success(f"Found PIXI task: {task}")

        except Exception as e:
            self.error(f"Error reading pyproject.toml: {e}")

    def validate_fastmcp_setup(self) -> None:
        """Validate FastMCP 2.0 server setup."""
        print("\n🔍 Validating FastMCP 2.0 setup...")

        server_path = self.project_root / "src" / "session_notes" / "server.py"
        if not server_path.exists():
            self.error("FastMCP server file not found: src/session_notes/server.py")
            return

        try:
            with open(server_path) as f:
                content = f.read()

            # Check for FastMCP imports
            if "from fastmcp import FastMCP" in content:
                self.success("Found FastMCP import")
            else:
                self.error("Missing FastMCP import")

            # Check for expected decorators
            expected_decorators = ["@app.tool()", "@app.resource("]
            for decorator in expected_decorators:
                if decorator in content:
                    self.success(f"Found FastMCP decorator: {decorator}")
                else:
                    self.warning(f"Missing FastMCP decorator: {decorator}")

            # Check for expected tools
            expected_tools = [
                "start_session",
                "end_session",
                "log_agent_execution",
                "log_tool_request",
            ]

            for tool in expected_tools:
                if f"def {tool}(" in content:
                    self.success(f"Found FastMCP tool: {tool}")
                else:
                    self.error(f"Missing FastMCP tool: {tool}")

        except Exception as e:
            self.error(f"Error reading server.py: {e}")

    def validate_security_setup(self) -> None:
        """Validate security scanning setup."""
        print("\n🔍 Validating security setup...")

        # Check pre-commit config
        precommit_path = self.project_root / ".pre-commit-config.yaml"
        if precommit_path.exists():
            try:
                with open(precommit_path) as f:
                    config = yaml.safe_load(f)

                # Check for security tools in pre-commit
                repos = [repo.get("repo", "") for repo in config.get("repos", [])]
                if any("bandit" in repo for repo in repos):
                    self.success("Found Bandit in pre-commit config")
                else:
                    self.warning("Bandit not configured in pre-commit")

            except yaml.YAMLError as e:
                self.error(f"Invalid pre-commit config: {e}")
        else:
            self.warning("Pre-commit config not found")

        # Check for .secrets.baseline
        secrets_baseline = self.project_root / ".secrets.baseline"
        if secrets_baseline.exists():
            self.success("Found .secrets.baseline file")
        else:
            self.warning("Consider adding .secrets.baseline for secret scanning")

    def validate_test_setup(self) -> None:
        """Validate testing configuration."""
        print("\n🔍 Validating test setup...")

        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            self.error("Tests directory not found")
            return

        # Check for test files
        test_files = list(tests_dir.glob("test_*.py"))
        if not test_files:
            self.warning("No test files found in tests directory")
        else:
            self.success(f"Found {len(test_files)} test files")

        # Check for pytest configuration in pyproject.toml
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return

        try:
            with open(self.project_root / "pyproject.toml", "rb") as f:
                config = tomllib.load(f)

            if "tool" in config and "pytest" in config["tool"]:
                pytest_config = config["tool"]["pytest"]
                if "ini_options" in pytest_config:
                    self.success("Found pytest configuration")

                    # Check for important pytest settings
                    ini_options = pytest_config["ini_options"]
                    if "asyncio_mode" in ini_options:
                        self.success("Found asyncio configuration for FastMCP")
                    if "timeout" in ini_options:
                        self.success("Found timeout configuration")
                else:
                    self.warning("Pytest ini_options not found")
            else:
                self.warning("Pytest configuration not found in pyproject.toml")

        except Exception as e:
            self.warning(f"Could not validate pytest config: {e}")

    def run_pixi_validation(self) -> None:
        """Run PIXI validation commands."""
        print("\n🔍 Running PIXI validation...")

        try:
            # Check if PIXI is available
            result = subprocess.run(
                ["pixi", "--version"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                self.success(f"PIXI available: {result.stdout.strip()}")
            else:
                self.warning("PIXI not available - install for full validation")
                return

            # Validate environments
            environments = ["quality", "quality-extended", "ci"]
            for env in environments:
                try:
                    result = subprocess.run(
                        ["pixi", "run", "-e", env, "python", "--version"],
                        capture_output=True,
                        text=True,
                        cwd=self.project_root,
                        timeout=30,
                    )

                    if result.returncode == 0:
                        self.success(f"PIXI environment '{env}' is functional")
                    else:
                        self.warning(f"PIXI environment '{env}' has issues")

                except subprocess.TimeoutExpired:
                    self.warning(f"PIXI environment '{env}' validation timed out")
                except Exception as e:
                    self.warning(f"Could not validate PIXI environment '{env}': {e}")

        except FileNotFoundError:
            self.warning("PIXI not found - install for full validation")
        except Exception as e:
            self.warning(f"PIXI validation error: {e}")

    def generate_report(self) -> None:
        """Generate validation report."""
        print("\n" + "=" * 80)
        print("📋 CI/CD VALIDATION REPORT")
        print("=" * 80)

        if not self.errors and not self.warnings:
            print("🎉 All validations passed! CI/CD setup is ready.")
            return

        if self.errors:
            print(f"\n🚨 ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        print("\n📊 SUMMARY:")
        print(f"  • Errors: {len(self.errors)}")
        print(f"  • Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n❌ CI/CD setup has critical issues that need to be resolved.")
            sys.exit(1)
        else:
            print("\n✅ CI/CD setup is functional with minor warnings.")

    def run_all_validations(self) -> None:
        """Run all validation checks."""
        print("🚀 Starting CI/CD Setup Validation for Session Notes FastMCP 2.0")
        print("=" * 80)

        self.validate_directory_structure()
        self.validate_workflow_syntax()
        self.validate_ci_config()
        self.validate_pixi_configuration()
        self.validate_fastmcp_setup()
        self.validate_security_setup()
        self.validate_test_setup()
        self.run_pixi_validation()

        self.generate_report()


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    validator = CIValidator(project_root)
    validator.run_all_validations()


if __name__ == "__main__":
    main()
