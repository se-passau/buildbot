import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, compile,
                                    s_sbranch, s_force, s_trigger, mkdir)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases
from buildbot.plugins import util
from buildbot.changes import filter

codebase = make_cb(['polli-sb'])
force_codebase = make_new_cb(['polli-sb'])

P = util.Property
BuildFactory = util.BuildFactory
accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    steps = [
        git('polli-sb', 'master', codebases, workdir="build/polli-sb"),
        cmd('cmake', "build/polli-sb",
            '-DCMAKE_BUILD_TYPE=Release',
            '-DBUILD_SHARED_LIBS=On',
            '-G', 'Ninja',
            env={
                "PATH": "/opt/cmake/bin:/usr/local/bin:/usr/bin:/bin"
            },
            name="cmake",
            description="[uchroot] cmake: release build",
            descriptionDone="[uchroot] configured."),
        compile("ninja",
                haltOnFailure=True, name="build jit",
                description="[uchroot] building PolyJIT",
                descriptionDone="[uchroot] built PolyJIT",
                timeout=4800)
    ]

    c['builders'].append(builder("polyjit-superbuild", None, accepted_builders,
                         factory=BuildFactory(steps)))
# yapf: enable


def schedule(c):
    c['schedulers'].extend([
        s_sbranch("branch-sched-polyjit-superbuild", codebase,
                  ["polyjit-superbuild"],
                  change_filter=filter.ChangeFilter(branch_re='master')),
        s_force("force-sched-polyjit-superbuild", force_codebase,
                ["polyjit-superbuild"]),
        s_trigger("trigger-sched-polyjit-superbuild", codebase,
                  ["polyjit-superbuild"])
    ])


register(sys.modules[__name__])
