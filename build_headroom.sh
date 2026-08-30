#!/bin/sh
# Build Headroom to PDF.
# Requires: texlive-luatex (for luaotfload / system-font access),
# the TeX Gyre fonts, and the Ubuntu font family.
set -e
lualatex -interaction=nonstopmode headroom.tex >/dev/null
lualatex -interaction=nonstopmode headroom.tex >/dev/null   # second pass
echo "headroom.pdf written"
