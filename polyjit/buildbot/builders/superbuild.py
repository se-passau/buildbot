import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, mkdir,
                                    ucmd, cmd, ucompile, ip,
                                    s_nightly, s_sbranch, s_force, s_trigger,
                                    hash_upload_to_master)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['polli-sb'])
force_codebase = make_new_cb(['polli-sb'])

P = util.Property
BuildFactory = util.BuildFactory

supported = {
    "debussy": slaves.infosun['debussy'],
    "ligeti": slaves.infosun['ligeti']
}
accepted_builders = slaves.get_hostlist(supported)


# yapf: disable
def configure(c):
    steps = [
        define("SUPERBUILD_ROOT", ip("%(prop:builddir)s/polli-sb")),
        define("UCHROOT_SUPERBUILD_ROOT", "/mnt/polli-sb"),
        define("POLYJIT_DEFAULT_BRANCH", "WIP-merge-next"),

        git('polli-sb', 'master', codebases, workdir=P("SUPERBUILD_ROOT"),
            mode="full", method="fresh"),
        ucmd('cmake', "--version",
             logEnviron=True,
             usePTY=False,
             env={
                 "PATH": ["/opt/cmake/bin", "/usr/local/bin", "/usr/bin", "/bin"]
             }),
        ucmd('cmake', P("UCHROOT_SUPERBUILD_ROOT"),
             '-DCMAKE_BUILD_TYPE=Release',
             '-DCMAKE_INSTALL_PREFIX=./_install',
             ip('-DPOLYJIT_BRANCH_CLANG=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
             ip('-DPOLYJIT_BRANCH_LLVM=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
             ip('-DPOLYJIT_BRANCH_POLLI=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
             ip('-DPOLYJIT_BRANCH_POLLY=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
             '-G', 'Ninja',
             env={
                 "PATH": ["/opt/cmake/bin", "/usr/local/bin", "/usr/bin", "/bin"]
             },
             mounts={
                 '%(prop:cmake_prefix)s' : "/opt/cmake"
             },
             usePTY=False,
             name="cmake",
             logEnviron=True,
             description="[uchroot] cmake: release build",
             descriptionDone="[uchroot] configured."),
        ucompile("ninja",
                 mounts={
                     '%(prop:cmake_prefix)s' : "/opt/cmake"
                 },
                 env={
                     "PATH": ["/opt/cmake/bin", "/usr/local/bin", "/usr/bin", "/bin"]
                 },
                 usePTY=False,
                 haltOnFailure=True, name="build jit",
                 description="[uchroot] building PolyJIT",
                 descriptionDone="[uchroot] built PolyJIT",
                 timeout=4800),
        cmd("tar", "czf", "../polyjit_sb.tar.gz", "-C", "./_install", ".")
    ]

    upload_pj = hash_upload_to_master(
        "polyjit_sb.tar.gz",
        "../polyjit_sb.tar.gz",
        "public_html/polyjit_sb.tar.gz", URL)
    steps.extend(upload_pj)

    c['builders'].append(
        builder("polyjit-superbuild", None,
                accepted_builders,
                tags=['polyjit'], factory=BuildFactory(steps)))
# yapf: enable


def schedule(c):
    c['schedulers'].extend([
        s_sbranch("branch-sched-polyjit-superbuild", codebase,
                  ["polyjit-superbuild"],
                  change_filter=filter.ChangeFilter(branch_re='master')),
        s_force("force-sched-polyjit-superbuild", force_codebase,
                ["polyjit-superbuild"]),
        s_trigger("trigger-sched-polyjit-superbuild", codebase,
                  ["polyjit-superbuild"]),
        s_nightly("nightly-sched-polyjit-superbuild", codebase,
                  ["polyjit-superbuild"],
                  hour=20, minute=0)
    ])


register(sys.modules[__name__])
