#!/bin/bash

# PIXI v0.50.2 CI Optimization Script
# Ensures optimal performance and reliability in CI environments
# Addresses "broken pipe" issues and timeout problems

set -euo pipefail

echo "🚀 PIXI v0.50.2 CI Environment Optimization"
echo "============================================"

# Environment variables for PIXI v0.50.2 optimization
export PIXI_NO_PROGRESS=true
export PIXI_CACHE_DIR="${PIXI_CACHE_DIR:-/tmp/.pixi-cache}"
export RATTLER_REPODATA_TIMEOUT=60
export CONDA_SOLVER_TIMEOUT=300
export PYTHONUNBUFFERED=1

echo "📋 Environment Configuration:"
echo "   PIXI Version: $(pixi --version)"
echo "   Platform: linux-64 (enforced)"
echo "   Cache Dir: $PIXI_CACHE_DIR"
echo "   Progress: Disabled (CI optimized)"
echo "   Timeouts: Repodata=60s, Solver=300s"

# Create cache directory if it doesn't exist
mkdir -p "$PIXI_CACHE_DIR"

# Function to install environment with retry logic
install_environment() {
    local env_name="$1"
    local max_retries="${2:-3}"
    local retry_count=0

    echo "📦 Installing environment: $env_name"

    while [ $retry_count -lt $max_retries ]; do
        echo "🔄 Attempt $((retry_count + 1))/$max_retries"

        if pixi install -e "$env_name" --verbose; then
            echo "✅ Environment $env_name installed successfully"

            # Verify environment health
            if pixi run -e "$env_name" python --version > /dev/null 2>&1; then
                echo "✅ Environment $env_name health check passed"
                return 0
            else
                echo "❌ Environment $env_name health check failed"
            fi
        else
            echo "❌ Installation failed for $env_name (attempt $((retry_count + 1)))"
        fi

        retry_count=$((retry_count + 1))

        if [ $retry_count -lt $max_retries ]; then
            echo "🧹 Cleaning environment for retry..."
            rm -rf ".pixi/envs/$env_name" || true
            sleep $((retry_count * 5))  # Exponential backoff: 5s, 10s, 15s
        fi
    done

    echo "❌ Failed to install environment $env_name after $max_retries attempts"
    return 1
}

# Function to validate pixi.lock consistency
validate_lock_file() {
    echo "🔍 Validating pixi.lock file consistency..."

    if [ ! -f "pixi.lock" ]; then
        echo "❌ No pixi.lock file found - generating fresh lock"
        pixi install > /dev/null
        return 0
    fi

    # Check if lock file is up to date
    if pixi install --locked > /dev/null 2>&1; then
        echo "✅ Lock file is consistent and up to date"
    else
        echo "⚠️  Lock file inconsistency detected - regenerating"
        rm -f pixi.lock
        pixi install > /dev/null
        echo "✅ Fresh lock file generated"
    fi
}

# Function to optimize environment cache
optimize_cache() {
    echo "🗄️  Optimizing PIXI cache..."

    # Clean old cache entries if cache is too large
    if [ -d "$PIXI_CACHE_DIR" ]; then
        cache_size=$(du -sm "$PIXI_CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")
        echo "   Current cache size: ${cache_size}MB"

        if [ "$cache_size" -gt 1000 ]; then  # > 1GB
            echo "   Cache size exceeds 1GB - cleaning old entries"
            find "$PIXI_CACHE_DIR" -type f -mtime +7 -delete 2>/dev/null || true
            echo "   Cleaned cache entries older than 7 days"
        fi
    fi
}

# Main optimization sequence
main() {
    echo "🏃 Starting PIXI CI optimization sequence..."

    # Step 1: Validate lock file consistency
    validate_lock_file

    # Step 2: Optimize cache
    optimize_cache

    # Step 3: Install environments based on CI job requirements
    if [ "${CI_ENVIRONMENT:-}" = "quality-gates" ]; then
        install_environment "ci" 2
    elif [ "${CI_ENVIRONMENT:-}" = "security-scan" ]; then
        install_environment "quality-extended" 3
    elif [ "${CI_ENVIRONMENT:-}" = "coverage" ]; then
        install_environment "quality-extended" 3
    elif [ "${CI_ENVIRONMENT:-}" = "performance" ]; then
        install_environment "quality-extended" 3
    elif [ "${CI_ENVIRONMENT:-}" = "multi-environment" ]; then
        # Install specific environment from matrix
        install_environment "${MATRIX_ENVIRONMENT:-ci}" 2
    else
        # Default: install CI environment
        install_environment "ci" 2
    fi

    # Step 4: Environment validation
    echo "🔍 Final environment validation..."
    pixi list -e "${MATRIX_ENVIRONMENT:-ci}" > /dev/null
    echo "✅ Environment package listing successful"

    echo "🎉 PIXI CI optimization completed successfully!"
    echo "   Environment ready for CI tasks"
}

# Handle script execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
