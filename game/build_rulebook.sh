#!/bin/sh
# Build the Fifteen Hands rulebook. Requires lualatex (texlive-luatex),
# TeX Gyre Pagella and the Ubuntu font family.
set -e
lualatex -interaction=nonstopmode rulebook.tex >/dev/null
lualatex -interaction=nonstopmode rulebook.tex >/dev/null
echo "rulebook.pdf written"
