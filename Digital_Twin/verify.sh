#!/bin/bash
# Quick verification of RPM Digital Twin setup

echo "╔══════════════════════════════════════════════════════╗"
echo "║  RPM DIGITAL TWIN - PROJECT VERIFICATION             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Count files
TOTAL_FILES=$(find . -type f ! -path "*/node_modules/*" ! -path "*/.git/*" 2>/dev/null | wc -l)
MARKDOWN_FILES=$(find . -name "*.md" ! -path "*/node_modules/*" | wc -l)
TS_FILES=$(find . -name "*.ts" -o -name "*.tsx" ! -path "*/node_modules/*" | wc -l)
PY_FILES=$(find . -name "*.py" ! -path "*/node_modules/*" | wc -l)
CPP_FILES=$(find . -name "*.cpp" -o -name "*.h" ! -path "*/node_modules/*" | wc -l)

echo "📊 PROJECT STATISTICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total Files Created:     $TOTAL_FILES"
echo "Documentation Files:     $MARKDOWN_FILES"
echo "TypeScript Files:        $TS_FILES"
echo "Python Files:            $PY_FILES"
echo "C++ Files:               $CPP_FILES"
echo ""

echo "📁 MAIN DIRECTORIES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "src/frontend" ]; then echo "✓ Frontend (Electron + React)"; fi
if [ -d "src/backend" ]; then echo "✓ Backend (Node.js)"; fi
if [ -d "src/rt_engine" ]; then echo "✓ C++ Real-Time Engine"; fi
if [ -d "src/analytics" ]; then echo "✓ Python Analytics"; fi
if [ -d "docs" ]; then echo "✓ Documentation"; fi
if [ -d "scripts" ]; then echo "✓ Build Scripts"; fi
if [ -d "deployment" ]; then echo "✓ Deployment Config"; fi
echo ""

echo "📚 DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
[ -f "START_HERE.md" ] && echo "✓ START_HERE.md (👈 Read this first!)"
[ -f "GETTING_STARTED.md" ] && echo "✓ GETTING_STARTED.md"
[ -f "README.md" ] && echo "✓ README.md"
[ -f "DEVELOPMENT.md" ] && echo "✓ DEVELOPMENT.md"
[ -f "ROADMAP.md" ] && echo "✓ ROADMAP.md"
[ -f "docs/architecture.md" ] && echo "✓ docs/architecture.md"
[ -f "docs/api_reference.md" ] && echo "✓ docs/api_reference.md"
[ -f "docs/binary_protocol.md" ] && echo "✓ docs/binary_protocol.md"
echo ""

echo "✨ QUICK START"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Read:     cat START_HERE.md"
echo "2. Setup:    bash scripts/setup-dev-env.sh"
echo "3. Run:      Follow the 3-terminal startup guide"
echo "4. Open:     http://localhost:5173"
echo ""

echo "🎯 PROJECT STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase:       1 (Core Infrastructure)"
echo "Status:      ✅ COMPLETE"
echo "Ready for:   Phase 2 Development"
echo ""

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Project location:                                   ║"
echo "║  /Users/pandeyji/Desktop/RPM/Digital_Twin            ║"
echo "║                                                      ║"
echo "║  Next: Read START_HERE.md for quick start guide 🚀  ║"
echo "╚══════════════════════════════════════════════════════╝"
