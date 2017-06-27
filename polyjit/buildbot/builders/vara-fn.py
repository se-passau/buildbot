import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, ip, s_sbranch, s_abranch,
                                    s_nightly, s_force, s_trigger,
                                    hash_upload_to_master)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

#codebase = make_cb(['vara', 'vara-llvm', 'vara-clang', 'compiler-rt'])
codebase = {
    'compiler-rt': {
        'repository': 'http://llvm.org/git/compiler-rt.git',
        'branch': 'release_40',
        'revision': None
    },
    'vara': {
        'repository': 'git@github.com:vulder/VaRA.git',
        'branch': 'vara-dev-fn',
        'revision': None
    },
    'vara-llvm': {
        'repository': 'git@github.com:vulder/vara-llvm.git',
        'branch': 'vara-llvm-dev-fn',
        'revision': None
    },
    'vara-clang': {
        'repository': 'git@github.com:vulder/vara-clang.git',
        'branch': 'vara-clang-dev-fn',
        'revision': None
    },
}
force_codebase = make_new_cb(['vara', 'vara-llvm', 'vara-clang', 'compiler-rt'])

P = util.Property
BuildFactory = util.BuildFactory

def can_build_llvm_debug(host):
    if "can_build_llvm_debug" in host["properties"]:
        return host["properties"]["can_build_llvm_debug"]
    return False

accepted_builders = slaves.get_hostlist(slaves.infosun, predicate=can_build_llvm_debug)


# yapf: disable
def configure(c):
    steps = [
        define("VARA_LLVM_ROOT", ip("%(prop:builddir)s/vara-fn-llvm")),
        define("UCHROOT_SRC_ROOT", "/mnt/vara-fn-llvm"),
        define("VARA_CLANG_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/tools/clang")),
        define("VARA_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/tools/VaRA")),
        define("COMPILERRT_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/projects/compiler-rt")),

        git('vara-llvm', 'vara-llvm-dev-fn', codebases, workdir=P("VARA_LLVM_ROOT")),
        git('vara-clang', 'vara-clang-dev-fn', codebases, workdir=P("VARA_CLANG_ROOT")),
        git('vara', 'vara-dev-fn', codebases, workdir=P("VARA_ROOT")),
        git('compiler-rt', 'release_40', codebases, workdir=P("COMPILERRT_ROOT")),
        ucmd('cmake', P("UCHROOT_SRC_ROOT"),
             '-DCMAKE_BUILD_TYPE=Debug',
             '-DCMAKE_C_FLAGS=-g -fno-omit-frame-pointer',
             '-DCMAKE_CXX_FLAGS=-g -fno-omit-frame-pointer',
             '-DBUILD_SHARED_LIBS=On',
             '-DLLVM_TARGETS_TO_BUILD=X86',
             '-DLLVM_BINUTILS_INCDIR=/usr/include',
             '-DLLVM_ENABLE_PIC=On',
             '-DLLVM_ENABLE_ASSERTIONS=On',
             '-DLLVM_ENABLE_TERMINFO=Off',
             '-G', 'Ninja',
             env={
                 "PATH": "/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin"
             },
             name="cmake",
             description="cmake O3, Assertions, PIC, Shared"),
        ucompile("ninja", haltOnFailure=True, name="build VaRA-fn"),
        ucompile("ninja", "check-vara-clang-RA", haltOnFailure=True, name="run VaRA-clang Region annotation regression tests"),
    ]

    c['builders'].append(builder("build-vara-fn", None, accepted_builders,
                         tags=['vara'], factory=BuildFactory(steps)))

def schedule(c):
    c['schedulers'].extend([
        s_abranch("build-vara-fn-sched", codebase, ["build-vara-fn"],
                  change_filter=filter.ChangeFilter(branch_re="vara-dev-fn|vara-llvm-dev-fn|vara-clang-dev-fn"),
                  treeStableTimer=5 * 60),
        s_force("force-build-vara-fn", force_codebase, ["build-vara-fn"]),
        s_trigger("trigger-build-vara-fn", codebase, ['build-vara-fn']),
    ])
# yapf: enable


register(sys.modules[__name__])
