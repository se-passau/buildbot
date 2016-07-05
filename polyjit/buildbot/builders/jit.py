import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, compile,
                                    upload_file, rmdir, ip, test, s_sbranch,
                                    s_force, s_trigger)
from polyjit.buildbot.repos import make_cb, codebases
from buildbot.plugins import util
from buildbot.changes import filter

cb_polli = make_cb(['polli', 'llvm', 'clang', 'polly', 'openmp', 'libcxx',
                    'libcxx_abi'])

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
    c['builders'].append(builder("build-jit", None, accepted_builders,
        factory = BuildFactory([
            define("scratch", P("scratch", default="/scratch/pjtest")),
            define("concurrency", P("concurrency", default="170")),
            define("cores", P("cores", default="10")),
            define("experiment", P("experiment", default="empty")),
            define("experiment-descriptor", ip("%(prop:buildername)s-%(prop:buildnumber)s")),
            define("MASTER_PREFIX", ip(ip_str)),
            define("LLVM_ARCHIVE", ip("llvm-" + ip_experiment + ".tar.gz")),
            define("MASTER_LLVM_ARCHIVE", ip("%(prop:MASTER_PREFIX)s/%(prop:LLVM_ARCHIVE)s")),
            define("LLVM_ROOT", ip("%(prop:builddir)s/llvm")),
            define("CLANG_ROOT", ip("%(prop:LLVM_ROOT)s/tools/clang")),
            define("POLLY_ROOT", ip("%(prop:LLVM_ROOT)s/tools/polly")),
            define("POLLI_ROOT", ip("%(prop:POLLY_ROOT)s/tools/polli")),
            define("OPENMP_ROOT", ip("%(prop:LLVM_ROOT)s/projects/openmp")),
            define("BUILD_PREFIX", ip("build/%(prop:experiment)s")),
            define("INSTALL_PREFIX", ip("%(prop:builddir)s/%(prop:experiment)s")),

            git('llvm', 'master', codebases, workdir=P("LLVM_ROOT")),
            git('clang', 'master', codebases, workdir=P("CLANG_ROOT")),
            git('polly', 'devel', codebases, workdir=P("POLLY_ROOT")),
            git('polli', ip(ip_branch), codebases, workdir=P("POLLI_ROOT"), submodules=True),
            git('openmp', 'master', codebases, workdir=P("OPENMP_ROOT")),
            cmd('cmake', P("LLVM_ROOT"),
                '-DCMAKE_BUILD_TYPE=Release',
                '-DCMAKE_C_COMPILER=clang-3.8',
                '-DCMAKE_CXX_COMPILER=clang++-3.8',
                '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
                ip('-DCMAKE_INSTALL_PREFIX=%(prop:INSTALL_PREFIX)s'),
                '-DBUILD_SHARED_LIBS=On',
                '-DCMAKE_USE_RELATIVE_PATHS=On',
                '-DPOLLY_BUILD_POLLI=On',
                '-DLLVM_TARGETS_TO_BUILD=X86',
                '-DLLVM_BINUTILS_INCDIR=/usr/include',
                '-DLLVM_ENABLE_PIC=On',
                '-DLLVM_ENABLE_ASSERTIONS=On',
                '-DLLVM_ENABLE_TERMINFO=Off',
                '-DCLANG_DEFAULT_OPENMP_RUNTIME=libomp',
                '-DPAPI_INCLUDE_DIR=/scratch/pjtest/papi/include/',
                '-DPAPI_LIBRARY=/scratch/pjtest/papi/lib/libpapi.so',
                '-DLIKWID_INCLUDE_DIR=/usr/include/',
                '-DLIKWID_LIBRARY=/usr/lib/liblikwid.so',
                '-DBOOST_ROOT=/scratch/pjtest/opt/boost_1_60_0',
                '-G',
                'Ninja',
                workdir=P("BUILD_PREFIX"),
                name="cmake",
                description="cmake O3, Assertions, PIC, Static"),
            compile("ninja",
                    workdir=P("BUILD_PREFIX"),
                    haltOnFailure=True,
                    name="build jit",
                    description=ip("build " + ip_experiment + " configuration")),
            test("ninja", "check-polli",
                 workdir=P("BUILD_PREFIX"),
                 name="check-polli",
                 description="run polli unit tests"),
            cmd("ninja", "install",
                workdir=P("BUILD_PREFIX"),
                name="deploy",
                description=ip("install " + ip_experiment + " version")),
            cmd("tar", "czf", P("LLVM_ARCHIVE"), P("experiment")),
            upload_file(P("LLVM_ARCHIVE"), P("MASTER_LLVM_ARCHIVE")),
            rmdir(P("INSTALL_PREFIX"), haltOnFailure=False,
                  name="clean install/", description="remove old install/")
        ])))
# yapf: enable

def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-jit-sched",
                  cb_polli,
                  ["build-jit"],
                  change_filter=filter.ChangeFilter(branch_re='next|develop'),
                  treeStableTimer=2 * 60),
        s_sbranch("build-jit-sched-daily",
                  cb_polli,
                  ["build-jit"],
                  change_filter=filter.ChangeFilter(branch_re='master'),
                  treeStableTimer=30 * 60), s_force(
                      "force-build-jit", cb_polli, ["build-jit"]), s_trigger(
                          "trigger-build-jit", cb_polli, ['build-jit'])
    ])


register(sys.modules[__name__])
