#!/bin/sh
# Build Headroom to PDF. Requires pdflatex with psnfss (mathpazo, avant).
set -e
pdflatex -interaction=nonstopmode headroom.tex >/dev/null
pdflatex -interaction=nonstopmode headroom.tex >/dev/null   # second pass
echo "headroom.pdf written"
