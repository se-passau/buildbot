import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, ucmd, ucompile,
                                    upload_file, download_file, ip, mkdir,
                                    rmdir, s_sbranch, s_force, s_trigger,
                                    cmddef)
from polyjit.buildbot.repos import make_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['polli', 'llvm', 'clang', 'polly', 'openmp', 'compiler-rt'])

P = util.Property
BuildFactory = util.BuildFactory
accepted_builders = slaves.get_hostlist(slaves.infosun)


def extract_rc(propertyname):
    name = propertyname
    def extract_rc_wrapper(rc, stdout, stderr):
        return { name: rc == 0 }
    return extract_rc_wrapper

def property_is_true(propname):
    prop = propname
    def property_is_true_wrapper(step):
        return bool(step.getProperty(prop))
    return property_is_true_wrapper

def property_is_false(propname):
    prop = propname
    def property_is_false_wrapper(step):
        return not bool(step.getProperty(prop))
    return property_is_false_wrapper


# yapf: disable
def configure(c):
    c['builders'].append(builder("build-jit", None, accepted_builders,
        factory = BuildFactory([
            define("POLLI_ROOT", ip("%(prop:builddir)s/polli")),
            define("POLLI_BUILD", ip("%(prop:builddir)s/")),
            define("UCHROOT_SRC_ROOT", "/mnt/polli"),
            cmddef(command="stat llvm.tar.gz",
                   extract_fn=extract_rc('have_llvm')),
            download_file(src="public_html/llvm.tar.gz.md5",
                          tgt="llvm.tar.gz.md5",
                          doStepIf=property_is_true("have_llvm")),
            cmddef(command="md5sum -c llvm.tar.gz.md5",
                   extract_fn=extract_rc('have_newest_llvm'),
                   doStepIf=property_is_true("have_llvm")),
            download_file(src="public_html/llvm.tar.gz",
                          tgt="llvm.tar.gz",
                          doStepIf=property_is_false("have_newest_llvm")),
            git('polli', 'next', codebases, workdir=P("POLLI_ROOT")),
            rmdir(ip(%)"build/llvm", doStepIf=property_is_false("have_newest_llvm")),
            mkdir("build/llvm"),
            mkdir("build/polli"),
            cmd("tar", "xzf", "llvm.tar.gz", "-C", ip("%(prop:builddir)s/llvm")),
            ucmd('cmake', P("UCHROOT_SRC_ROOT"),
                 '-DLLVM_DIR=/mnt/llvm/lib/cmake/llvm',
                 '-DLLVM_INSTALL_ROOT=/mnt/llvm',
                 '-DPOLLY_INSTALL_ROOT=/mnt/llvm/lib/libPolly.a',
                 '-DCMAKE_BUILD_TYPE=Release',
                 '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
                 '-DBUILD_SHARED_LIBS=Off',
                 '-G', 'Ninja',
                 env={
                     "PATH": "/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin"
                 },
                 name="cmake",
                 description="cmake O3, Assertions, PIC, Static"),
            ucompile("ninja", haltOnFailure=True, name="build jit"),
            cmd("tar", "czf", "../polyjit.tar.gz", "."),
            upload_file(src="../polyjit.tar.gz",
                        tgt="public_html/polyjit.tar.gz",
                        url=URL + "/polyjit.tar.gz")
        ])))
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
