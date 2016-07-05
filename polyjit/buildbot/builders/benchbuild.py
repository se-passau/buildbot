import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, git, cmd, rmdir, pylint,
                                    s_sbranch, s_force, s_trigger)
from polyjit.buildbot.repos import make_cb, codebases

from buildbot.plugins import util
from buildbot.changes import filter

BuildFactory = util.BuildFactory
ip_branch = "%(prop:branch:~next)s"
ip_experiment = "%(prop:experiment:~empty)s"
ip_scratch = "%(prop:scratch:~/scratch/pjtest)s"
ip_dirname = "%(prop:dirname:~empty)s"
ip_str = ip_scratch + "/" + ip_dirname

cb_benchbuild = make_cb(['benchbuild', 'stats'])
accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    c['builders'].append(builder("build-benchbuild", None, accepted_builders,
        factory=BuildFactory([
            git('benchbuild', 'develop', codebases),
            cmd("virtualenv", "-p", "python3.4", "_venv",
                name="create virtualenv",
                description="setup benchbuild virtual environment"),
            cmd("_venv/bin/pip3", "install", ".",
                name="install benchbuild",
                description="install benchbuild into the venv",
                env={'PYTHONPATH': 'benchbuild/bin',
                     'HOME': '.'}),
            pylint("_venv/bin/pylint", "./benchbuild/",
                   warnOnFailure=True, flunkOnWarnings=False,
                   flunkOnFailure=False, haltOnFailure=False),
            pylint("_venv/bin/pylint", "-E", "./benchbuild/",
                   warnOnFailure=True, flunkOnWarnings=False,
                   flunkOnFailure=False, haltOnFailure=False),
            rmdir("_venv")
        ])))
# yapf: enable


def schedule(c):
    c['schedulers'].append([
        s_sbranch("build-benchbuild-sched",
                  cb_benchbuild,
                  ["build-benchbuild"],
                  change_filter=filter.ChangeFilter(branch='develop'),
                  treeStableTimer=2 * 60),
        s_force("force-build-benchbuild", cb_benchbuild, ["build-benchbuild"]),
        s_trigger("trigger-build-benchbuild", cb_benchbuild,
                  ["build-benchbuild"])
    ])


register(sys.modules[__name__])
