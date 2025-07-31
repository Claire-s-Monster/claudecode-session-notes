# Agent Context Directory

This directory tracks sub-agent executions during session-20250730-152733.

## Structure

Each sub-agent execution creates a directory with the following structure:
```
agents/
├── <agent-type>-<timestamp>/
│   ├── agent-context.json      # Agent execution metadata
│   ├── input.json              # Input parameters and prompt
│   ├── output.json             # Agent response and results
│   ├── tools-used.json         # Tools invoked during execution
│   └── decisions.json          # Decisions made by this agent
```

## Agent Types Tracked

- general-purpose: Multi-step research and complex task execution
- pixi-optimizer: pyproject.toml optimization and pixi configuration
- project-initializer: Basic project structure creation
- cross-platform-implementer: Docker-to-native conversions
- conflict-resolver: Merge conflicts and systematic resolution
- mcp-integration-manager: MCP usage compliance management
- action-reorganizer: GitHub Actions workflow restructuring
- status-checker: Quick system status checks
- prompt-builder: Task() call optimization
- dependency-mapper: Project dependency relationship mapping
- context-compressor: Context size reduction for delegation
- project-scanner: Quick project structure detection
- ci-reporter: CI/CD metrics analysis and insights
- ci-maintainer: CI workflow maintenance and optimization
- ci-creator: CI/CD workflow bootstrapping
- quality-enforcer: Zero-tolerance quality gate enforcement
- test-coverage-analyzer: Detailed test coverage analysis
- security-scanner: Security vulnerability scanning
- atomic-design-validator: Component hierarchy validation
- pyproject-toml-validator: pyproject.toml compliance validation
- pyproject-toml-updater: Surgical pyproject.toml modifications
- pyproject-toml-creator: New pyproject.toml creation
- dependency-resolver: pip-to-conda package translation
- git-initializer: Git repository initialization
- git-conflict-resolver: Complex git conflict resolution
- git-basic-workflow: Simple git operations
- mcp-fallback-handler: MCP failure recovery
- error-recovery-specialist: General error analysis and recovery
- emergency-coordinator: Critical system failure management
- context-transfer-handler: Context transfer failure handling
- checkpoint-manager: Operation recovery point management

## Usage

Agent context files are automatically created when sub-agents are invoked via the Task tool.
