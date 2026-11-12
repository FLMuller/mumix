r"""texhtml.py  A small LaTeX to HTML converter for the recording book (the doc block of the report server cannot load MathJax).

    math(latex)      the html of a formula: subscripts and superscripts, Greek letters, fractions stacked, square roots, text in upright
    inline(markup)   markup with formulas between \( and \): each formula is converted (math), the rest is kept as it is
    css()            the style rules the output needs (the book puts them in its page)

What it understands. Letters: a single letter is italic, two or more are upright (Re, max, ivs); the names of functions (max, min, ln, log, exp,
sin, cos, erf) are upright. Greek letters and the usual symbols by name (\alpha ... \omega, \Gamma, \Delta, \times, \cdot, \approx, \sim, \le, \ge,
\pm, \infty, \partial, \nabla, \to, \propto, \langle, \rangle ...). _x and _{...}, ^x and ^{...}; \frac{a}{b} and \dfrac (stacked); \sqrt{a} (with the bar);
\text{...} and \mathrm{...} (upright); \tilde{x}, \bar{x}, \hat{x}, \dot{x} (a mark over the letter); \left and \right (the bracket is kept);
\quad, \qquad, \, \; \! (spaces). A command it does not know is written as it is, in red, so it can be seen and added.

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import re

__all__ = ["math", "inline", "css"]

GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
         "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ", "varphi": "φ", "chi": "χ",
         "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω"}
SYMBOLS = {"times": "×", "cdot": "·", "approx": "≈", "sim": "∼", "simeq": "≃", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "pm": "±", "mp": "∓", "infty": "∞",
           "partial": "∂", "nabla": "∇", "to": "→", "rightarrow": "→", "propto": "∝", "langle": "⟨", "rangle": "⟩", "ne": "≠", "neq": "≠", "equiv": "≡",
           "ll": "≪", "gg": "≫", "dots": "…", "ldots": "…", "cdots": "⋯", "int": "∫", "sum": "∑", "prod": "∏", "deg": "°", "circ": "°", "prime": "′",
           "lbrace": "{", "rbrace": "}", "ast": "*", "star": "⋆"}
FUNCTIONS = {"max", "min", "ln", "log", "exp", "sin", "cos", "tan", "erf", "sinh", "cosh", "tanh", "arctan", "lim", "det", "Re", "Im"}
SPACES = {"quad": "&emsp;", "qquad": "&emsp;&emsp;", ",": "&thinsp;", ";": "&nbsp;", "!": "", " ": " ", ":": "&nbsp;"}
MARKS = {"tilde": "~", "bar": "¯", "hat": "^", "dot": "˙", "vec": "→", "overline": "¯"}


def group(s, i):
    """(the text inside the braces that open at s[i], the index after the closing brace) or (the one character at i, i + 1)."""
    if i >= len(s):
        return "", i
    if s[i] != "{":
        return s[i], i + 1
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def command(s, i):
    """(the name of the command that starts at the backslash s[i], the index after it)."""
    j = i + 1
    if j < len(s) and not s[j].isalpha():
        return s[j], j + 1
    while j < len(s) and s[j].isalpha():
        j += 1
    return s[i + 1:j], j


def word(text):
    """A run of letters: a function name or a name of two or more letters upright, a single letter italic."""
    return "<i>%s</i>" % text if len(text) == 1 else text


def parse(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            name, i = command(s, i)
            if name in GREEK:
                out.append("<i>%s</i>" % GREEK[name])
            elif name in SYMBOLS:
                out.append(SYMBOLS[name])
            elif name in FUNCTIONS:
                out.append(name)
            elif name in SPACES:
                out.append(SPACES[name])
            elif name in ("frac", "dfrac", "tfrac"):
                a, i = group(s, i)
                b, i = group(s, i)
                out.append("<span class=\"fr\"><span class=\"nu\">%s</span><span class=\"de\">%s</span></span>" % (parse(a), parse(b)))
            elif name == "sqrt":
                a, i = group(s, i)
                out.append("√<span class=\"ov\">%s</span>" % parse(a))
            elif name in ("text", "mathrm", "textrm", "mbox", "operatorname"):
                a, i = group(s, i)
                out.append("<span class=\"up\">%s</span>" % a)
            elif name in ("mathbf", "boldsymbol", "bf"):
                a, i = group(s, i)
                out.append("<b>%s</b>" % parse(a))
            elif name in MARKS:
                a, i = group(s, i)
                out.append("<span class=\"acc\" data-m=\"%s\">%s</span>" % (MARKS[name], parse(a)))
            elif name in ("left", "right"):
                if i < len(s):
                    out.append("" if s[i] == "." else ("{" if s[i:i + 2] == "\\{" else s[i]))
                    i += 2 if s[i:i + 2] in ("\\{", "\\}") else 1
            elif name in ("(", ")", "[", "]", "|", "%", "&", "#", "_", "{", "}"):
                out.append(name)
            else:
                out.append("<span class=\"bad\">\\%s</span>" % name)
        elif c == "_" or c == "^":
            a, i2 = group(s, i + 1)
            tag = "sub" if c == "_" else "sup"
            if c == "^" and i2 < len(s) and s[i2] == "_":                       # x^a_b: both, stacked
                b, i3 = group(s, i2 + 1)
                out.append("<span class=\"ss\"><sup>%s</sup><sub>%s</sub></span>" % (parse(a), parse(b)))
                i = i3
                continue
            out.append("<%s>%s</%s>" % (tag, parse(a), tag))
            i = i2
        elif c == "{":
            a, i = group(s, i)
            out.append(parse(a))
        elif c.isalpha():
            j = i
            while j < len(s) and s[j].isalpha():
                j += 1
            run = s[i:j]
            out.append(run if run in FUNCTIONS else word(run) if len(run) == 1 else "<span class=\"up\">%s</span>" % run)
            i = j
        elif c == "~":
            out.append("&nbsp;")
            i += 1
        elif c == "-":
            out.append("−")
            i += 1
        elif c == "'":
            out.append("′")
            i += 1
        elif c == "*":
            out.append("∗")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def math(latex):
    """The html of one formula (an inline span; the book puts a display formula in a div of its own)."""
    return "<span class=\"m\">%s</span>" % parse(latex)


def inline(markup):
    """The markup with each \\( ... \\) formula converted."""
    return re.sub(r"\\\((.*?)\\\)", lambda found: math(found.group(1)), markup, flags=re.S)


def css():
    return """
.m{font-family:'Times New Roman',Times,serif;font-size:1.08em;white-space:nowrap}
.m i{font-style:italic}
.m .up{font-style:normal}
.m sub,.m sup{font-size:70%;line-height:0}
.m .fr{display:inline-block;vertical-align:middle;text-align:center;margin:0 2px}
.m .fr .nu{display:block;padding:0 3px;border-bottom:1px solid currentColor}
.m .fr .de{display:block;padding:0 3px}
.m .ov{border-top:1px solid currentColor;padding:0 1px}
.m .ss{display:inline-block;vertical-align:middle;line-height:1}
.m .ss sup,.m .ss sub{display:block;font-size:70%}
.m .acc{position:relative;display:inline-block}
.m .acc:before{content:attr(data-m);position:absolute;top:-0.55em;left:0;width:100%;text-align:center;font-size:90%}
.m .bad{color:#c00;font-family:Consolas,monospace}
.k-eq .body .m{font-size:1.2em}
"""
