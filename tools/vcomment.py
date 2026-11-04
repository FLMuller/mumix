r"""vcomment.py -- review a project's code in a browser: its files in a tree on the left, each file
a tab you can write comments on, saved into the file as comment lines (nothing else is ever
changed). The layout and the code pane are those of a runbench report; the report server
(reportserver.py) answers the page, through vcserver.py.

Use:     python vcomment.py [path] [-repo NAME] [-title TEXT] [-files NAME ...] [-open] [-nostart]
  path     a file or folder; the project is its repository (the first folder up with .git) or, with
           none, the top folder under the Claude root. Default: the current folder. It never goes
           above the reach of the path: the first folder up that holds .claude, or is one name
           below the drive root. The drive root (C:/) is never read.
  -repo    a top folder of the Claude root, by name (instead of a path).
  -title   words for the page: which project this is, or why the files are open.
  -files   file names (or the end of a path, a/b.py) to open as tabs at the start. Each is looked
           for downward from the project root: the match nearest the root wins, and of equals the
           newest. A name that is not found is said so and left out.
  -open    open the page in the browser (os.startfile); otherwise the path is printed.
  -nostart do not start the report server (it is started when it is not running).
  The page is results/<review-NAME>_<date>_<time>.html, a folder beside this folder, and every
  run makes a new one. The console shows its path. Exit code: 0 done; 2 nothing to review (a path
  outside the reach, a -repo that is not a folder).

Python:  vcomment(path='', repo='', title='', files=(), open_page=False, start=True,
                  results=None, claude_root=None, server=True) -> the page's path
  server       False: touch nothing of the report server (no registering, no start): the page is
               made with no port, which is what the tests use.
  results      the folder for the page, instead of the one beside this folder.
  claude_root  the folder -repo names a folder of, instead of the first one up from this file that
               holds .claude.

The page asks the report server (port 47651) for the tree and for each file; the page's file name
is the token, and vcserver.register ties it to the repository. reportserver.handlers (beside
reportserver.roots) names vcserver, which is how the report server learns the verbs. A report
server that was running before that file was written has to be restarted once (open
.claude/vscripts/reportserver.bat and use the verb restart). If the server is not running, the
page's run opens that bat in a window (rsrv.ensure) and the bat starts it.

VERSION  M1 m01.v02 (2026-11-03): the server is opened through .claude/vscripts/reportserver.bat
         (rsrv.ensure); the page's tree, find, splitter and comment box changed (primary/html).
         M1 m01.v01 (2026-11-01): first version.
"""
import html
import json
import os
import re
import sys
import time

# the support modules are in primary/ below this file: use finds them there
from use import load, use

use('primary', 'silent')
import codelex
import reportserver as rsrv
import vcserver
from htmlwriter import htmsave, htmtemplate
load('marked', 'mdwriter')            # md2htm, mdwriteln: built by use into primary/pyxfiles

__all__ = ['vcomment']

HERE = os.path.dirname(os.path.abspath(__file__))
PRIMARY = os.path.join(HERE, 'primary')
TEMPLATE = os.path.join(PRIMARY, 'html', 'vcomment.html')
CSS = os.path.join(PRIMARY, 'html', 'runbench.css')
JS = os.path.join(PRIMARY, 'html', 'runbench.js')
VCCSS = os.path.join(PRIMARY, 'html', 'vcomment.css')
VCJS = os.path.join(PRIMARY, 'html', 'vcomment.js')
LETTERS = [chr(97 + i) for i in range(26)]


def literal(value):
    """A value as a JavaScript literal for the page (a closing tag cannot end the script)."""
    return json.dumps(value).replace('</', '<\\/')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def choose_root(path, repo, claude_root):
    """(root, why not): the project folder, by -repo or by the path. See the module header."""
    if repo:
        if not re.fullmatch(r'[^\\/:*?"<>|]+', repo) or repo in ('.', '..'):
            return None, f'-repo {repo!r} is not a folder name'
        root = os.path.join(claude_root, repo)
        if not os.path.isdir(root):
            return None, f'-repo {repo}: no folder {root}'
        return root, ''
    here = os.path.abspath(path or os.getcwd())
    root = vcserver.find_root(here)
    if root is None:
        return None, f'{here} is outside any reach (no .claude or top folder above it)'
    return root, ''


def welcome(name, root, title, found, missing):
    """The Start tab: the project, the title, the files that were asked for."""
    md = mdwriteln(None, '_\\tab:Start/_')
    mdwriteln(md, f'## {name}' + (f': {title}' if title else ''))
    mdwriteln(md, f'\nProject folder: `{root}`\n')
    mdwriteln(md, '- Click a file in the tree to open it as a tab (orange in the tree); click it '
                  'again to close its tab. An html file opens in a new browser tab. The arrow in '
                  'the tree\'s header folds the tree away.')
    mdwriteln(md, '- Click the number of a line (or its margin) to write a comment on it; a comment '
                  'is saved into the file as lines of the language\'s comment marker and your '
                  'initials, nothing else in the file changes.')
    mdwriteln(md, '- The file is read when you open it, so a file you changed since is shown as it '
                  'is now. Close its tab and click it again to read it afresh.')
    if found:
        mdwriteln(md, '\nOpened at the start: ' + ', '.join(f'`{x}`' for x in found))
    if missing:
        mdwriteln(md, '\nNot found: ' + ', '.join(f'`{x}`' for x in missing))
    return md


def page_name(results, stem, now):
    """A new file name for the page, the series name and the minute as the report server reads
    them: stem_YYYY.MM.DD_HH;MM.html, then with the seconds, then with letters."""
    local = time.localtime(now)
    base = f'{stem}_{time.strftime("%Y.%m.%d_%H;%M", local)}'
    names = [base, base + time.strftime('.%S', local)]
    names += [names[1] + letter for letter in LETTERS]
    for name in names:
        if not os.path.exists(os.path.join(results, name + '.html')):
            return name + '.html'
    raise FileExistsError(f'vcomment: no free name for {stem}')


def vcomment(path='', repo='', title='', files=(), open_page=False, start=True, results=None,
             claude_root=None, server=True):
    """Make the page for a project and return its path; see the module header. A SystemExit(2)
    says what could not be reviewed."""
    top = claude_root or vcserver.reach_limit(HERE)
    root, why = choose_root(path, repo, top)
    if root is None:
        print('vcomment: ' + why)
        raise SystemExit(2)
    name = os.path.basename(root) or root
    hits = vcserver.find_files(root, list(files)) if files else []
    found = [rel for _, rel in hits if rel]
    missing = [asked for asked, rel in hits if rel is None]
    folder = results or os.path.join(os.path.dirname(HERE), 'results')
    os.makedirs(folder, exist_ok=True)
    stem = 'review-' + re.sub(r'[^A-Za-z0-9.\-]+', '-', name)[:50]
    now = time.time()
    filename = page_name(folder, stem, now)
    bat, port = '', 0
    if server:
        bat, port = rsrv.prepare(folder), rsrv.PORT       # the folder is read by the report server
        handlers = os.path.splitext(rsrv.files()[0])[0] + '.handlers'
        known = read(handlers).split() if os.path.isfile(handlers) else []
        if 'vcserver' not in known:
            with open(handlers, 'w', encoding='utf-8') as f:
                f.write('\n'.join(known + ['vcserver']) + '\n')
            print('vcomment: the report server now loads vcserver; if it was running, restart '
                  'it (reportserver.bat, then the verb restart)')
        vcserver.register(filename, root, os.path.dirname(rsrv.files()[0]))
    heading = f'vcomment: {name}' + (f' - {title}' if title else '')
    body = bytes(md2htm(welcome(name, root, title, found, missing)))
    page = htmtemplate(TEMPLATE, body, TITLE=html.escape(heading), STEM=literal(stem), RUNS='[]',
                       NAME=literal(filename), TOKEN=literal(rsrv.token(filename, now)),
                       PORT=port, BAT=literal(bat),
                       VC=literal({'root': root, 'title': heading, 'open': found}),
                       css=CSS, js=JS, rolecss=codelex.css(), vccss=read(VCCSS), vcjs=read(VCJS))
    out = htmsave(page, os.path.join(folder, filename))
    if server and start:
        print(rsrv.ensure('vcomment', rsrv.PORT, *rsrv.files()))
    for asked in missing:
        print(f'vcomment: not found under {root}: {asked}')
    print(f'project: {root}')
    print('page: ' + out)
    if open_page:
        os.startfile(out)
    return out


def words(argv):
    """The console words as the arguments of vcomment(). A word it does not know, or a value
    missing, prints the Use lines and exits with 2."""
    args = {}
    files = []
    k = 0
    while k < len(argv):
        word = argv[k]
        k += 1
        if word in ('-title', '-repo'):
            if k >= len(argv):
                print(__doc__.split('Python:')[0])
                raise SystemExit(2)
            args[word[1:]] = argv[k]
            k += 1
        elif word == '-files':
            while k < len(argv) and not argv[k].startswith('-'):
                files.append(argv[k])
                k += 1
        elif word == '-open':
            args['open_page'] = True
        elif word == '-nostart':
            args['start'] = False
        elif word.startswith('-') or 'path' in args:
            print(__doc__.split('Python:')[0])
            raise SystemExit(2)
        else:
            args['path'] = word
    if files:
        args['files'] = files
    return args


def main(argv):
    vcomment(**words(argv))
    raise SystemExit(0)


if __name__ == '__main__':
    main(sys.argv[1:])
