import re, sys

FILES = [
    "/mnt/user-data/outputs/salt-harrow-part1-draft.md",
    "/mnt/user-data/outputs/salt-harrow-scenes-4-9-draft.md",
    "/mnt/user-data/outputs/salt-harrow-scene7-draft.md",
    "/mnt/user-data/outputs/salt-harrow-scene10-draft.md",
    "/mnt/user-data/outputs/salt-harrow-scene11-draft.md",
    "/mnt/user-data/outputs/salt-harrow-coda-draft.md",
]

scenes = {}
current = None
scene_re = re.compile(r"Scene (\d+)")

for path in FILES:
    current = None
    with open(path) as f:
        for raw in f.read().splitlines():
            line = raw.rstrip()
            if line.startswith("#"):
                m = scene_re.search(line)
                if m:
                    current = int(m.group(1))
                    scenes[current] = []
                continue
            if current is None:
                continue
            scenes[current].append(line)

# sanity check
expected = list(range(1, 14))
missing = [n for n in expected if n not in scenes]
if missing:
    sys.exit(f"missing scenes: {missing}")

def to_paras(lines):
    paras, buf = [], []
    for ln in lines:
        if ln.strip() == "":
            if buf:
                paras.append(" ".join(buf))
                buf = []
        else:
            buf.append(ln.strip())
    if buf:
        paras.append(" ".join(buf))
    return paras

def tex_escape(s):
    s = s.replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
    s = s.replace("#", r"\#").replace("_", r"\_")
    # opening single quotes: apostrophe at start or after space/bracket
    s = re.sub(r"(^|[\s(\[])'", r"\1`", s)
    return s

# guard: no em dashes anywhere
for n, lines in scenes.items():
    for ln in lines:
        assert "—" not in ln and "---" not in ln, f"em dash in scene {n}"

PART_STARTS = {1: ("I", "The Commission"), 4: ("II", "The Trial"), 12: ("III", "The Summer Assizes")}

body = []
for n in expected:
    if n in PART_STARTS:
        num, name = PART_STARTS[n]
        body.append(f"\\partheading{{{num}}}{{{name}}}")
    else:
        body.append("\\scenebreak")
    paras = to_paras(scenes[n])
    for i, p in enumerate(paras):
        p = tex_escape(p)
        if i == 0:
            body.append("\\noindent " + p)
        else:
            body.append(p)
        body.append("")

body_tex = "\n".join(body)

preamble = r"""\documentclass[11pt]{article}
\usepackage[paperwidth=6.14in,paperheight=9.21in,textwidth=4.3in,textheight=7.1in,hcentering,vcentering]{geometry}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{mathpazo}
\usepackage[protrusion=true,expansion=true]{microtype}
\usepackage{lettrine}
\linespread{1.08}
\setlength{\parindent}{1.2em}
\setlength{\parskip}{0pt}
\frenchspacing

\pagestyle{plain}

\newcommand{\scenebreak}{%
  \par\vspace{1.1\baselineskip}%
  {\centering $\ast$\quad$\ast$\quad$\ast$\par}%
  \vspace{1.1\baselineskip}\noindent}

\newcommand{\partheading}[2]{%
  \clearpage
  \vspace*{5\baselineskip}
  {\centering
   {\large\scshape Part #1}\par
   \vspace{0.6\baselineskip}
   {\Large\itshape #2}\par}
  \vspace{2.5\baselineskip}\noindent}

\begin{document}

% ---------- Title page ----------
\thispagestyle{empty}
\vspace*{9\baselineskip}
{\centering
  {\huge\scshape The Cunning Woman\\[0.5\baselineskip] of Salt Harrow\par}
  \vspace{2\baselineskip}
  {\large\itshape Being a relation of the trial of Margery Ashe\\ at the Lent Assizes, in the year 1709\par}
  \vspace{6\baselineskip}
  {\small He casteth forth his ice like morsels:\\ who can stand before his cold?\par}
  \vspace{0.4\baselineskip}
  {\small\scshape Psalm 147\par}
}
\clearpage
\setcounter{page}{1}

"""

ending = r"""
\vspace{2\baselineskip}
{\centering\scshape the end\par}

\end{document}
"""

with open("./story.tex", "w") as f:
    f.write(preamble + body_tex + ending)

print("scenes:", sorted(scenes), "paras total:", sum(len(to_paras(v)) for v in scenes.values()))
