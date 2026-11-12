r"""check_maths.py  v01  Check the formulas of the generated pages: the paper and the tabs of the recording book.

    python check_maths.py            prints one line a page; exit code 1 if a page has a fault

For each page (scripts, styles and inline svg figures left out):
    delimiters   as many \( as \), an even number of $$
    braces       every formula has as many { as }
    commands     every \command inside a formula is one MathJax knows (the list KNOWN: base, ams, boldsymbol); an unknown one is shown in red by MathJax
    stray        a \command outside any formula (it would be printed as text)
    nesting      a \( inside a formula; an html tag inside a formula
    dollars      a single $ outside formulas (it could open a formula in another reader)
This checks the source text.  Whether the browser sets the formulas is checked in the report server (snap: the number of mjx-container elements).

Versions  M01 m01.v01 (2026-11-12): first version.
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)

__all__ = ["check", "main"]

KNOWN = set("""alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta kappa lambda mu nu xi pi rho sigma tau phi varphi chi psi omega
Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega frac dfrac tfrac sqrt left right big Big bigg Bigg bigl bigr Bigl Bigr quad qquad text mathrm mathbf mathit mathcal
mathbb boldsymbol bar hat tilde vec dot ddot overline underline langle rangle le ge leq geq ne neq approx sim simeq equiv propto to rightarrow leftarrow infty partial
nabla cdot cdots ldots dots times pm mp int oint sum prod lim max min ln log exp sin cos tan sinh cosh tanh arctan erf det sup inf Re Im ell hbar prime circ deg
ast star mid parallel perp in notin subset cup cap forall exists gg ll binom displaystyle textstyle scriptstyle operatorname begin end aligned align cases array
matrix pmatrix label tag nonumber hspace vspace phantom underbrace overbrace stackrel atop over choose bmod pmod Rightarrow Leftrightarrow iff implies neg land lor
oplus otimes dagger angle triangle square gtrsim lesssim xrightarrow xleftarrow Longleftrightarrow Longrightarrow boxed""".split()) | set(",;:!|{}()[]_%&#$ ") | {"\\"}


def check(text):
    """(number of formulas, list of faults) of the html text of a page."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", text, flags=re.S)
    faults = []
    opened, closed = len(re.findall(r"\\\(", body)), len(re.findall(r"\\\)", body))
    if opened != closed:
        faults.append("%d \\( against %d \\)" % (opened, closed))
    if body.count("$$") % 2:
        faults.append("an odd number of $$")
    formulas = re.findall(r"\\\((.*?)\\\)", body, re.S) + re.findall(r"\$\$(.*?)\$\$", body, re.S)
    unknown = collections.Counter()
    for m in formulas:
        for c in re.findall(r"\\([A-Za-z]+|.)", m):
            if c not in KNOWN:
                unknown[c] += 1
        if m.count("{") != m.count("}"):
            faults.append("braces do not match in: " + m[:70])
        if "\\(" in m:
            faults.append("a \\( inside a formula: " + m[:70])
        if re.search(r"<[a-zA-Z/]", m):
            faults.append("an html tag inside a formula: " + m[:70])
    if unknown:
        faults.append("commands MathJax does not know: %s" % dict(unknown))
    outside = re.sub(r"\$\$.*?\$\$", "", re.sub(r"\\\(.*?\\\)", "", body, flags=re.S), flags=re.S)
    stray = collections.Counter(re.findall(r"\\[A-Za-z]{2,}", outside))
    if stray:
        faults.append("commands outside any formula: %s" % dict(stray.most_common(8)))
    single = len(re.findall(r"(?<!\$)\$(?!\$)", outside))
    if single:
        faults.append("%d single $ outside formulas" % single)
    return len(formulas), faults


def main():
    pages = [os.path.join(LIT, "vortex-energy-balance.html")] + sorted(glob.glob(os.path.join(LIT, "record", "tabs", "*.html")))
    bad = 0
    for path in pages:
        with open(path, encoding="utf-8") as f:
            n, faults = check(f.read())
        bad += bool(faults)
        print("%-30s %5d formulas  %s" % (os.path.basename(path), n, "ok" if not faults else "FAULTS: " + " | ".join(faults[:6])))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
