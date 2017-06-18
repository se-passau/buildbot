import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, ucmd, ucompile, cmd,
                                    upload_file, ip, s_sbranch,
                                    s_nightly, s_force, s_trigger,
                                    hash_upload_to_master)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['vara', 'vara-llvm', 'vara-clang', 'compiler-rt'])
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
        define("VARA_LLVM_ROOT", ip("%(prop:builddir)s/vara-llvm")),
        define("UCHROOT_SRC_ROOT", "/mnt/vara-llvm"),
        define("VARA_CLANG_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/tools/clang")),
        define("VARA_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/tools/VaRA")),
        define("COMPILERRT_ROOT", ip("%(prop:VARA_LLVM_ROOT)s/projects/compiler-rt")),

        git('vara-llvm', 'vara-llvm-dev', codebases, workdir=P("VARA_LLVM_ROOT")),
        git('vara-clang', 'vara-clang-dev', codebases, workdir=P("VARA_CLANG_ROOT")),
        git('vara', 'vara-dev', codebases, workdir=P("VARA_ROOT")),
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
        ucompile("ninja", haltOnFailure=True, name="build VaRA"),
        ucompile("ninja", "check-vara", haltOnFailure=True, name="run VaRA regression tests"),
    ]

    c['builders'].append(builder("build-vara", None, accepted_builders,
                         tags=['vara'], factory=BuildFactory(steps)))

def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-vara-sched", codebase, ["build-vara"],
                  change_filter=filter.ChangeFilter(branch_re="vara-dev|vara-dev-jb-buildbot"),
                  treeStableTimer=2 * 60),
        s_force("force-build-vara", force_codebase, ["build-vara"]),
        s_trigger("trigger-build-vara", codebase, ['build-vara']),
        s_nightly("nightly-sched-build-vara", codebase,
                  ["build-vara"],
                  hour=22, minute=0)
    ])
# yapf: enable


register(sys.modules[__name__])
