import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, ucmd, ucompile,
                                    upload_file, trigger, ip, mkdir,
                                    rmdir, s_sbranch, s_force, s_trigger,
                                    hash_download_from_master,
                                    property_is_false, clean_unpack)
from polyjit.buildbot.repos import make_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['benchbuild'])

P = util.Property
BuildFactory = util.BuildFactory
accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    llvm_dl = hash_download_from_master("public_html/llvm.tar.gz",
                                        "llvm.tar.gz", "llvm")
    polyjit_dl = hash_download_from_master("public_html/polyjit.tar.gz",
                                        "polyjit.tar.gz", "polyjit")
    steps = [
        trigger(schedulerNames=['trigger-build-llvm', 'trigger-build-jit']),
    ]
    steps.extend(llvm_dl)
    steps.extend(clean_unpack("llvm.tar.gz", "llvm"))
    steps.extend(polyjit_dl)
    steps.extend(clean_unpack("polyjit.tar.gz", "polyjit"))
    steps.extend([
        define("BENCHBUILD_ROOT", ip("%(prop:builddir)s/build/benchbuild/")),
        git('benchbuild', 'develop', codebases, workdir=P("BENCHBUILD_ROOT")),

    ])

    steps.extend([
        ucmd('virtualenv', '-ppython3', 'env/'),
        ucmd('env/bin/pip3', 'install', P("BENCHBUILD_ROOT")),
        ucmd('env/bin/benchbuild', 'bootstrap', env={
            'BB_ENV_COMPILER_PATH': '/mnt/build/llvm/bin:/mnt/build/polyjit/bin',
            'BB_ENV_COMPILER_LD_LIBRARY_PATH': '/mnt/build/llvm/lib:/mnt/build/polyjit/lib',
            'BB_ENV_LOOKUP_PATH': '/mnt/build/llvm/lib:/mnt/build/polyjit/bin',
            'BB_ENV_LOOKUP_LD_LIBRARY_PATH': '/mnt/build/llvm/lib:/mnt/build/polyjit/lib',
            'BB_LLVM_DIR': '/mnt/build/llvm',
            'BB_LIKWID_PREFIX': '/usr/local',
            'BB_PAPI_INCLUDE': '/usr/include',
            'BB_PAPI_LIBRARY': '/usr/lib',
            'BB_SRC_DIR': '/mnt/build/benchbuild',
            'BB_UNIONFS_ENABLE': 'false'
        })
    ])

    c['builders'].append(builder("build-slurm-set", None, accepted_builders,
        factory=BuildFactory(steps)))
# yapf: enable

def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-slurm-set-sched", codebase, ["build-slurm-set"],
                  change_filter=filter.ChangeFilter(branch_re='next|develop'),
                  treeStableTimer=2 * 60),
        s_force("force-build-slurm-set", codebase, ["build-slurm-set"]),
        s_trigger("trigger-slurm-set", codebase, ['build-slurm-set'])
    ])


register(sys.modules[__name__])
