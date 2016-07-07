import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, rmdir, ip, test, s_sbranch,
                                    s_force, s_trigger)
from polyjit.buildbot.repos import make_cb, codebases
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['llvm', 'clang', 'polly', 'openmp', 'compiler-rt'])

P = util.Property
BuildFactory = util.BuildFactory
ip_branch = "%(prop:branch:~next)s"
ip_experiment = "%(prop:experiment:~empty)s"
ip_scratch = "%(prop:scratch:~/scratch/pjtest)s"
ip_dirname = "%(prop:dirname:~empty)s"
ip_str = ip_scratch + "/" + ip_dirname

accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    c['builders'].append(builder("build-llvm", None, accepted_builders,
        factory = BuildFactory([
            #define("scratch", P("scratch", default="/scratch/pjtest")),
            #define("MASTER_PREFIX", ip(ip_str)),
            #define("LLVM_ARCHIVE", ip("llvm-" + ip_experiment + ".tar.gz")),
            #define("MASTER_LLVM_ARCHIVE", ip("%(prop:MASTER_PREFIX)s/%(prop:LLVM_ARCHIVE)s")),
            define("LLVM_ROOT", ip("%(prop:builddir)s/llvm")),
            define("UCHROOT_SRC_ROOT", "/mnt/llvm"),
            define("CLANG_ROOT", ip("%(prop:LLVM_ROOT)s/tools/clang")),
            define("POLLY_ROOT", ip("%(prop:LLVM_ROOT)s/tools/polly")),
            define("COMPILERRT_ROOT", ip("%(prop:LLVM_ROOT)s/projects/compiler-rt")),
            define("OPENMP_ROOT", ip("%(prop:LLVM_ROOT)s/projects/openmp")),
            #define("INSTALL_PREFIX", ip("%(prop:builddir)s/%(prop:experiment)s")),

            git('llvm', 'master', codebases, workdir=P("LLVM_ROOT")),
            git('clang', 'master', codebases, workdir=P("CLANG_ROOT")),
            git('polly', 'devel', codebases, workdir=P("POLLY_ROOT")),
            git('compiler-rt', 'master', codebases, workdir=P("COMPILERRT_ROOT")),
            git('openmp', 'master', codebases, workdir=P("OPENMP_ROOT")),
            ucmd('cmake', P("UCHROOT_SRC_ROOT"),
                 '-DCMAKE_BUILD_TYPE=Release',
                 '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
                 '-DBUILD_SHARED_LIBS=Off',
                 '-DPOLLY_BUILD_POLLI=Off',
                 '-DLLVM_TARGETS_TO_BUILD=X86',
                 '-DLLVM_BINUTILS_INCDIR=/usr/include',
                 '-DLLVM_ENABLE_PIC=On',
                 '-DLLVM_ENABLE_ASSERTIONS=On',
                 '-DLLVM_ENABLE_TERMINFO=Off',
                 '-DCLANG_DEFAULT_OPENMP_RUNTIME=libomp',
                 '-G', 'Ninja',
                 env={
                     "PATH": "/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin"
                 },
                 name="cmake",
                 description="cmake O3, Assertions, PIC, Static"),
            ucompile("ninja", haltOnFailure=True, name="build jit"),
            cmd("tar", "czf", "llvm-polyjit.tar.gz", "-C", "build", "."),
            upload_file(src="llvm-polyjit.tar.gz", tgt="public_html",
                        url="")
        ])))

def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-llvm-sched", codebase, ["build-llvm"],
                  change_filter=filter.ChangeFilter(branch_re='master|next|develop'),
                  treeStableTimer=2 * 60),
        s_force("force-build-llvm", codebase, ["build-llvm"]),
        s_trigger("trigger-build-llvm", codebase, ['build-llvm'])
    ])
# yapf: enable


register(sys.modules[__name__])
