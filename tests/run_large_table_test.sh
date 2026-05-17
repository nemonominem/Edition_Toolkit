#!/bin/bash
# Test large tables in all three wrapping contexts
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate python_313x
cd /Users/gillesdemaneuf/Work/Edition/tests

echo "=== intelligence style ==="
python3 /Users/gillesdemaneuf/Work/Edition/md_to_pdf/etk_md2pdf/convert.py \
    test_columns.md --css intelligence test_columns_intelligence.pdf 2>&1

echo ""
echo "=== magazine style ==="
python3 /Users/gillesdemaneuf/Work/Edition/md_to_pdf/etk_md2pdf/convert.py \
    test_columns.md --css magazine test_columns_magazine.pdf 2>&1
