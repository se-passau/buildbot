import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, ucmd, ucompile,
                                    upload_file, ip, mkdir,
                                    rmdir, s_sbranch, s_force, s_trigger,
                                    property_is_false,
                                    hash_download_from_master)
from polyjit.buildbot.repos import make_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['polli', 'isl', 'isl-cpp', 'likwid'])

P = util.Property
BuildFactory = util.BuildFactory
accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    steps = [
        define("POLLI_ROOT", ip("%(prop:builddir)s/build/polli")),
        define("ISL_ROOT", ip("%(prop:builddir)s/build/isl")),
        define("ISL_CPP_ROOT", ip("%(prop:POLLI_ROOT)s/include/isl")),
        define("LIKWID_ROOT", ip("%(prop:builddir)s/build/likwid")),
        define("UCHROOT_SRC_ROOT", "/mnt/build/polli"),
        define("UCHROOT_LIKWID_SRC_ROOT", "/mnt/build/likwid"),
        define("UCHROOT_POLLI_BUILDDIR", "/mnt/build/build-polli"),
        define("UCHROOT_ISL_SRC_ROOT", "/mnt/build/isl")
    ]
    llvm_dl = hash_download_from_master("public_html/llvm.tar.gz",
                                        "llvm.tar.gz", "llvm")
    steps.extend(llvm_dl)
    steps.extend([
        git('likwid', 'v4.1', codebases, workdir=P("LIKWID_ROOT")),
        git('polli', 'next', codebases, workdir=P("POLLI_ROOT"),
            submodules=True),
        git('isl', 'isl-0.16.1-cpp', codebases, workdir=P("ISL_ROOT")),
        git('isl-cpp', 'master', codebases, workdir=P("ISL_CPP_ROOT")),
        rmdir("build/llvm",
            doStepIf=property_is_false("have_newest_llvm")),
        mkdir("build/llvm"),
        cmd("tar", "xzf", "llvm.tar.gz", "-C", "llvm",
            doStepIf=property_is_false("have_newest_llvm"),
            description="Unpacking LLVM"),
        mkdir("build/build-polli"),
        ucmd('./autogen.sh',
            workdir='build/isl/',
            env={
                "PATH": "/usr/sbin:/sbin:/usr/bin:/bin",
                "LC_ALL": "C"
            }, description="[uchroot] autogen isl"),
        ucmd('./configure', workdir='build/isl',
            description="[uchroot] configuring isl",
            descriptionDone="[uchroot] configured isl"),
        ucmd('make', '-C', P("UCHROOT_ISL_SRC_ROOT"),
            description="[uchroot] building isl",
            descriptionDone="[uchroot] built isl"),
        ucmd('make', '-C', P("UCHROOT_LIKWID_SRC_ROOT"), "install",
            description="[uchroot] building likwid",
            descriptionDone="[uchroot] built likwid"),
        ucmd('cmake', P("UCHROOT_SRC_ROOT"),
             '-DLLVM_INSTALL_ROOT=/mnt/build/llvm',
             '-DPOLLY_INSTALL_ROOT=/mnt/build/llvm',
             '-DISL_INSTALL_ROOT=/mnt/build/isl',
             '-DLIKWID_INSTALL_ROOT=/usr/local/',
             '-DCMAKE_BUILD_TYPE=Release',
             '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
             '-DBUILD_SHARED_LIBS=Off',
             '-G', 'Ninja',
             workdir='build/build-polli',
             env={
                 "PATH": "/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin"
             },
             name="cmake",
             description="[uchroot] cmake O3, Assertions, PIC, Static",
             descriptionDone="[uchroot] configured PolyJIT"),
        ucompile("ninja", "-C", P("UCHROOT_POLLI_BUILDDIR"),
                 haltOnFailure=True, name="build jit",
                 description="[uchroot] building PolyJIT",
                 descriptionDone="[uchroot] built PolyJIT"),
        cmd("tar", "czf", "polyjit.tar.gz", "build-polli",
            description="Packing PolyJIT",
            descriptionDone="Packed PolyJIT"),
        upload_file(src="polyjit.tar.gz",
                    tgt="public_html/polyjit.tar.gz",
                    url=URL + "/polyjit.tar.gz",
                    description="Uploading PolyJIT",
                    descriptionDone="Uploaded PolyJIT")
    ])

    c['builders'].append(builder("build-jit", None, accepted_builders,
        factory=BuildFactory(steps)))
# yapf: enable

def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-jit-sched", codebase, ["build-jit"],
                  change_filter=filter.ChangeFilter(branch_re='next|develop'),
                  treeStableTimer=2 * 60),
        s_force("force-build-jit", codebase, ["build-jit"]),
        s_trigger("trigger-build-jit", codebase, ['build-jit'])
    ])


register(sys.modules[__name__])
