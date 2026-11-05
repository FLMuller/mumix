import importlib.util, os, subprocess, sys, sysconfig
from pathlib import Path
from Cython.Compiler import Main
here = Path(__file__).resolve().parent
out = here / 'pyxfiles'
out.mkdir(exist_ok=True)
NO = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
for name in ('tiny', 'npy'):
    c = out / (name + '.c')
    Main.compile(str(here / (name + '.pyx')), language_level=3, output_file=str(c),
                 include_path=[str(here)], full_module_name=name)
    includes = [sysconfig.get_paths()['include']]
    if importlib.util.find_spec('numpy'):
        import numpy
        includes.append(numpy.get_include())
    base = Path(sys.base_prefix)
    pyd = out / (name + sysconfig.get_config_var('EXT_SUFFIX'))
    cmd = ['gcc', '-shared', '-O1', '-w', '-s', *['-I' + d for d in includes], str(c),
           *['-L' + str(d) for d in (base / 'libs', base) if d.is_dir()],
           f'-lpython{sys.version_info.major}{sys.version_info.minor}', '-o', str(pyd)]
    done = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO)
    print(name, 'gcc returned', done.returncode, done.stderr[-200:])
    r = subprocess.run([sys.executable, '-c',
        f'import sys; sys.path.insert(0, {str(out)!r}); import {name}; print({name}.{"add(2, 3)" if name == "tiny" else "one()"})'],
        capture_output=True, text=True, creationflags=NO)
    print('  import:', r.returncode, r.stdout.strip(), r.stderr.strip()[-200:])
    print('  sizes:', pyd.stat().st_size, '| exported PyInit:', end=' ')
    nm = subprocess.run(['nm', '-g', str(pyd)], capture_output=True, text=True, creationflags=NO)
    print([l for l in nm.stdout.splitlines() if 'PyInit' in l] or nm.stderr[:60] or 'stripped (-s)')
