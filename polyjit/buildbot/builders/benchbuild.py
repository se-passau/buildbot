import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, git, cmd, rmdir, pylint,
                                    s_sbranch, s_force, s_trigger, s_nightly)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases

from buildbot.plugins import util
from buildbot.changes import filter

BuildFactory = util.BuildFactory
ip_branch = "%(prop:branch:~next)s"
ip_experiment = "%(prop:experiment:~empty)s"
ip_scratch = "%(prop:scratch:~/scratch/pjtest)s"
ip_dirname = "%(prop:dirname:~empty)s"
ip_str = ip_scratch + "/" + ip_dirname

cb_benchbuild = make_cb(['benchbuild', 'stats'])
force_codebase = make_new_cb(['benchbuild', 'stats'])
accepted_builders = slaves.get_hostlist(slaves.infosun)


# yapf: disable
def configure(c):
    c['builders'].append(
        builder("build-benchbuild", None, accepted_builders,
                tags=['polyjit'],
                factory=BuildFactory([
                    git('benchbuild', 'develop', codebases),
                    cmd("virtualenv", "-p", "python3", "_venv",
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
                    rmdir("_venv")])))
# yapf: enable


def schedule(c):
    c['schedulers'].extend([
        s_sbranch("build-benchbuild-sched",
                  cb_benchbuild,
                  ["build-benchbuild"],
                  change_filter=filter.ChangeFilter(branch='develop'),
                  treeStableTimer=2 * 60),
        s_force("force-build-benchbuild", force_codebase, ["build-benchbuild"]),
        s_trigger("trigger-build-benchbuild", cb_benchbuild,
                  ["build-benchbuild"]),
        s_nightly("nightly-sched-build-benchbuild", cb_benchbuild,
                  ["build-benchbuild"],
                  hour=20, minute=0)
    ])


register(sys.modules[__name__])
