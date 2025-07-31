#!/usr/bin/env python3
"""
LOCAL Development Quality Gates Validator
Zero-tolerance policy enforcement for LOCAL development workflow.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class LocalQualityGates:
    """LOCAL development quality gates with zero-tolerance policy."""

    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.failed_checks: List[str] = []

    def run_command(self, name: str, cmd: str, critical: bool = True) -> bool:
        """Run a quality check command and capture results."""
        print(f"🔍 {name}...")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ {name}: FAILED")
            if result.stdout:
                print(f"   STDOUT: {result.stdout.strip()}")
            if result.stderr:
                print(f"   STDERR: {result.stderr.strip()}")

            if critical:
                self.failed_checks.append(name)
                return False
            else:
                print("   ⚠️  Non-critical failure")
        else:
            print(f"✅ {name}: PASSED")

        self.results[name] = result.returncode == 0
        return True

    def validate_environment(self) -> bool:
        """Validate LOCAL development environment setup."""
        print("\n🔧 ENVIRONMENT VALIDATION")
        print("=" * 50)

        checks = [
            ("PIXI Environment", "pixi --version"),
            ("Python Version", "python --version"),
            ("Git Repository", "git status --porcelain"),
        ]

        all_passed = True
        for name, cmd in checks:
            if not self.run_command(name, cmd, critical=False):
                all_passed = False

        return all_passed

    def run_quality_gates(self) -> bool:
        """Run core quality gates with zero-tolerance policy."""
        print("\n🚨 ZERO-TOLERANCE QUALITY GATES")
        print("=" * 50)

        # Core quality gates (MUST PASS)
        core_gates = [
            ("Unit Tests", "pixi run test"),
            ("Critical Linting", "pixi run lint"),
            ("Type Checking", "pixi run typecheck"),
            ("Test Coverage", "pixi run test-cov"),
        ]

        all_passed = True
        for name, cmd in core_gates:
            if not self.run_command(name, cmd, critical=True):
                all_passed = False

        return all_passed

    def run_pre_commit_validation(self) -> bool:
        """Run pre-commit hooks validation."""
        print("\n🪝 PRE-COMMIT HOOKS VALIDATION")
        print("=" * 50)

        return self.run_command(
            "Pre-commit Hooks", "pixi run pre-commit", critical=True
        )

    def run_extended_quality(self) -> bool:
        """Run extended quality checks (non-blocking)."""
        print("\n📊 EXTENDED QUALITY ANALYSIS")
        print("=" * 50)

        extended_checks = [
            ("Full Linting", "pixi run lint-full"),
            ("Format Check", "pixi run format-check"),
        ]

        all_passed = True
        for name, cmd in extended_checks:
            if not self.run_command(name, cmd, critical=False):
                all_passed = False

        return all_passed

    def generate_report(self) -> None:
        """Generate comprehensive quality report."""
        print("\n📋 QUALITY VALIDATION REPORT")
        print("=" * 50)

        total_checks = len(self.results)
        passed_checks = sum(1 for passed in self.results.values() if passed)

        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {total_checks - passed_checks}")

        if self.failed_checks:
            print("\n🛑 CRITICAL FAILURES (Zero-Tolerance):")
            for check in self.failed_checks:
                print(f"   ❌ {check}")

        if not self.failed_checks:
            print("\n✅ QUALITY GATES: ALL PASSED")
            print("🚀 READY FOR COMMIT")
        else:
            print(f"\n🚫 QUALITY GATES: {len(self.failed_checks)} CRITICAL FAILURES")
            print("🛑 COMMIT BLOCKED - Fix required")

    def run_full_validation(self) -> bool:
        """Run complete LOCAL quality validation."""
        print("🎯 LOCAL DEVELOPMENT QUALITY GATES")
        print("=" * 60)

        # Environment validation
        self.validate_environment()

        # Core quality gates (blocking)
        core_passed = self.run_quality_gates()

        # Pre-commit validation (blocking)
        precommit_passed = self.run_pre_commit_validation()

        # Extended quality (non-blocking)
        self.run_extended_quality()

        # Generate report
        self.generate_report()

        # Return overall result
        return core_passed and precommit_passed


def main():
    """Main entry point for LOCAL quality validation."""
    validator = LocalQualityGates()

    # Check if we're in the right directory
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("❌ Error: Not in project root (pyproject.toml not found)")
        sys.exit(1)

    # Run validation
    success = validator.run_full_validation()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
