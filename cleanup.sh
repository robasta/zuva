#!/bin/bash
# Sunsynk Dashboard Cleanup Script
# Removes temporary files, logs, and build artifacts

echo "🧹 Starting Sunsynk Dashboard cleanup..."

# Remove Python cache files
echo "Removing Python cache files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove log files
echo "Removing log files..."
find . -name "*.log" -delete
rm -f sunsynk-dashboard/backend/backend.log
rm -f sunsynk-dashboard/backend/nohup.out

# Remove Node.js dependencies (if needed)
echo "Removing node_modules..."
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "package-lock.json" -delete 2>/dev/null || true

# Remove build artifacts
echo "Removing build artifacts..."
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove IDE files
echo "Removing IDE files..."
find . -name ".vscode" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".idea" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true

# Remove OS files
echo "Removing OS files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

# Docker cleanup (optional)
echo "Docker cleanup available with: docker system prune"

echo "✅ Cleanup complete!"
echo ""
echo "📊 Project status:"
ls -la sunsynk-dashboard/
echo ""
echo "🚀 To start Phase 3 dashboard:"
echo "1. Backend: cd sunsynk-dashboard/backend && PYTHONPATH=/path/to/sunsynk-api-client python3 main.py"
echo "2. Frontend: cd sunsynk-dashboard/simple-frontend && python3 -m http.server 3000"
echo "3. Access: http://localhost:3000"
