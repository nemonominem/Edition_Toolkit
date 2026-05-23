#!/bin/bash
# Test large tables in all three wrapping contexts
# Uses local source CSS explicitly to bypass the installed package's stale CSS
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate python_313x
cd /Users/gillesdemaneuf/Work/Edition/tests

CONVERT=/Users/gillesdemaneuf/Work/Edition/md_to_pdf/etk_md2pdf/convert.py
CSS_DIR=/Users/gillesdemaneuf/Work/Edition/md_to_pdf/etk_md2pdf/styles

echo "=== intelligence style ==="
python3 $CONVERT test_columns.md \
    --css $CSS_DIR/style_intelligence.css \
    test_columns_intelligence.pdf 2>&1

echo ""
echo "=== magazine style ==="
python3 $CONVERT test_columns.md \
    --css $CSS_DIR/style_magazine.css \
    test_columns_magazine.pdf 2>&1
