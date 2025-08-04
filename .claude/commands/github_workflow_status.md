# GitHub Workflow Status - Remote Integration Monitoring

Monitor GitHub workflow status, CI/CD pipeline health, and remote collaboration metrics for the session-notes FastMCP 2.0 project.

## Execution Steps

### 1. Repository Status Assessment
```bash
# Check current branch and tracking
git status --porcelain --branch
git log --oneline -3

# Remote tracking verification
git remote -v
git branch -vv
```

### 2. CI/CD Pipeline Health Check
```bash
# GitHub CLI workflow status (if available)
gh workflow list 2>/dev/null || echo "GitHub CLI not configured"
gh pr checks 2>/dev/null || echo "No active PR or GitHub CLI unavailable"

# Check for workflow files
ls -la .github/workflows/
```

### 3. Quality Gate Status
```bash
# Run local quality checks to mirror CI
echo "🔍 Running quality gate validation..."

# Test coverage check
pixi run -e quality-extended coverage report --format=total 2>/dev/null || echo "Coverage data unavailable"

# Lint status
pixi run -e quality-extended ruff check --quiet --statistics . 2>/dev/null || echo "Lint check unavailable"

# Type checking
pixi run -e quality-extended mypy --quiet src/ 2>/dev/null || echo "Type check unavailable"
```

### 4. FastMCP 2.0 Compliance Verification
```bash
# Validate server can start (quick check)
echo "🚀 FastMCP 2.0 server validation..."
timeout 3s pixi run -e ci server &
SERVER_PID=$!
sleep 1
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ MCP server starts successfully"
    kill $SERVER_PID 2>/dev/null
else  
    echo "❌ MCP server startup failed"
fi
```

### 5. Remote Collaboration Metrics
```bash
# Check for pending changes that need committing
STAGED=$(git diff --cached --name-only | wc -l)
MODIFIED=$(git diff --name-only | wc -l)
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l)

echo "📊 Repository State:"
echo "  Staged files: $STAGED"
echo "  Modified files: $MODIFIED"
echo "  Untracked files: $UNTRACKED"

# Last commit attribution check
LAST_COMMIT=$(git log -1 --pretty=format:"%s")
if echo "$LAST_COMMIT" | grep -q "Co-Authored-By: MementoRC"; then
    echo "✅ Last commit includes proper attribution"
else
    echo "⚠️  Last commit missing MementoRC attribution"
fi
```

### 6. Performance Metrics
```bash
# Environment health check
echo "🔧 Environment Status:"
pixi info --quiet 2>/dev/null || echo "PIXI environment issues detected"

# Recent build artifacts
if [ -f "coverage.xml" ]; then
    echo "✅ Coverage report available"
fi

if [ -d "htmlcov" ]; then
    echo "✅ HTML coverage report available"  
fi
```

## Success Criteria

- All quality gates passing locally
- Repository state is clean or properly staged
- FastMCP 2.0 server can start successfully
- Proper commit attribution is maintained
- CI/CD pipeline configuration is healthy

## Output Format

```
GITHUB WORKFLOW STATUS
======================
BRANCH: [current-branch]
REMOTE: [tracking-status]
QUALITY: [passing/failing]
FASTMCP: [operational/issues]
ATTRIBUTION: [compliant/missing]

CI/CD PIPELINE: [healthy/issues]
COVERAGE: [percentage]%
SECURITY: [scan-status]

READY FOR: [push/PR/merge]
```

## Integration Notes

- Use this command before pushing changes to remote
- Validates all critical quality gates locally
- Ensures remote collaboration standards are met
- Provides quick health check for distributed team workflows
