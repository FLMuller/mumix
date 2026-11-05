import sys, traceback
from pathlib import Path
here = Path(__file__).resolve().parent
log = []
log.append(f'stderr is {sys.stderr!r}, stdout is {sys.stdout!r}')
try:
    from Cython.Compiler import Main
    result = Main.compile(str(here / 'bad.pyx'), language_level=3, output_file=str(here / 'pyxfiles' / 'bad.c'),
                          include_path=[str(here)], full_module_name='bad')
    log.append(f'returned num_errors={result.num_errors}')
except BaseException:
    log.append('RAISED ' + traceback.format_exc()[-400:])
(here / 'pyw_out.txt').write_text('\n'.join(log), encoding='utf-8')
