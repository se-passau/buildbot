import sys

from ..builders import register
from ..utils import (builder, define, git, cmd, rmdir, ip, benchbuild_slurm, trigger, s_trigger, s_force)
from ..repos import make_cb, codebases
from .. import slaves
from buildbot.plugins import util
from buildbot.plugins import *

P = util.Property
cb_chimaira = make_cb(['polli', 'llvm', 'clang', 'polly', 'openmp', 'benchbuild'])
cb_benchbuild = make_cb(['benchbuild', 'stats'])
accepted_builders = slaves.get_hostlist(slaves.infosun)

exps = {
    "raw" : {
        "exclusive" : "true",
        "experiment" : "raw",
        "dirname" : "raw",
        "group": ["polybench", "benchbuild", "lnt", "gentoo"]
    },
    "pj-raw": {
        "exclusive" : "true",
        "experiment" : "pj-raw",
        "dirname" : "pj-raw",
        "group": ["polybench", "benchbuild", "lnt", "gentoo"]
    },
    "pj-papi": {
        "exclusive" : "true",
        "experiment" : "pj-papi",
        "dirname" : "pj-papi",
        "group": ["polybench", "benchbuild", "lnt", "gentoo"]
    },
    "cs": {
        "cores": P("cores", default="1"),
        "exclusive" : "false",
        "experiment" : "cs",
        "dirname" : "cs",
    },
    "pj-cs": {
        "cores": P("cores", default="1"),
        "exclusive" : "false",
        "experiment" : "pj-cs",
        "dirname" : "pj-cs",
    },
    "pj-collect": {
        "cores": P("cores", default="1"),
        "exclusive" : "false",
        "experiment" : "pj-collect",
        "dirname" : "pj-collect",
    },
    "polly": {
        "exclusive" : "true",
        "experiment" : "polly",
        "dirname" : "polly",
    },
    "polly-openmp": {
        "exclusive" : "true",
        "experiment" : "polly-openmp",
        "dirname" : "polly-openmp",
    },
    "polly-openmpvect" : {
        "exclusive" : "true",
        "experiment" : "polly-openmpvect",
        "dirname" : "polly-openmpvect",
    },
    "polly-vectorize" : {
        "exclusive" : "true",
        "experiment" : "polly-vectorize",
        "dirname" : "polly-vectorize",
    },
    "perf-pj-papi" : {
        "exclusive" : "true",
        "experiment" : "pj-papi",
        "dirname" : "perf-pj-papi",
        "branch" : "perf",
    }
}

BuildFactory = util.BuildFactory
ip_branch = "%(prop:branch:~next)s"
ip_experiment = "%(prop:experiment:~empty)s"
ip_scratch = "%(prop:scratch:~/scratch/pjtest)s"
ip_dirname = "%(prop:dirname:~empty)s"
ip_str = ip_scratch + "/" + ip_dirname
SetPropertiesFromEnv = steps.SetPropertiesFromEnv

def configure(c):
    c['builders'].append(builder("spawn-chimaira", None, accepted_builders,
        factory = BuildFactory([
            SetPropertiesFromEnv(variables=["PATH"]),
            define("scratch", P("scratch", default="/scratch/pjtest")),
            define("concurrency", P("concurrency", default="170")),
            define("cores", P("cores", default="10")),
            define("experiment", P("experiment", default="empty")),
            define("experiment-descriptor", ip("%(prop:buildername)s-%(prop:buildnumber)s")),
            define("BB_PREFIX", ip(ip_str + "/benchbuild")),
            define("BB_PATH", ip(ip_str + "/benchbuild/bin:/usr/bin:/bin:/usr/local/bin:/sbin:/bin:%(prop:PATH)s")),
            define("BB_SRC_DIR", ip(ip_str + "/benchbuild-study")),
            define("BB_TMP_DIR", ip(ip_scratch + "/src")),
            define("BB_BUILD_DIR", ip(ip_str + "/run")),
            define("BB_CONFIG_FILE", ip(ip_scratch + "/.benchbuild.json")),
            define("SLURM_SCRIPT", ip(ip_experiment + "-slurm.sh")),
            define("MASTER_PREFIX", ip(ip_str)),
            define("LLVM_ARCHIVE", ip("llvm-" + ip_experiment + ".tar.gz")),
            define("BB_LLVM_DIR", P("BB_LLVM_DIR")),
            define("MASTER_LLVM_ARCHIVE", ip("%(prop:MASTER_PREFIX)s/%(prop:LLVM_ARCHIVE)s")),
            git('benchbuild', "develop", codebases, workdir=P("BB_SRC_DIR")),
            rmdir(P("BB_PREFIX"), haltOnFailure=False),
            cmd("virtualenv", "-p", "python3.4", "--clear", "--always-copy", P("BB_PREFIX"),
                name="create benchbuild virtualenv",
                description="create benchbuild virtualenv"),
            cmd("pip3", "install", P("BB_SRC_DIR"),
                name="install benchbuild-study",
                description="install benchbuild study into the venv",
                env={'PATH': P("BB_PATH"),
                     'PYTHONPATH': ip(ip_str + '/benchbuild/bin'),
                     'HOME': '.'}),
            cmd(benchbuild_slurm,
                name="create slurm array job script",
                description="create slurm array job script",
                workdir=P("BB_SRC_DIR"),
                env={
                    'PATH': P("BB_PATH"),
                    'BB_PATH': P("BB_PATH"),
                    'BB_SRC_DIR': P("BB_SRC_DIR"),
                    'BB_TMP_DIR': P("BB_TMP_DIR"),
                    'BB_BUILD_DIR': P("BB_BUILD_DIR"),
                    'BB_LLVM_DIR': P("BB_LLVM_DIR"),
                    'BB_SLURM_CPUS_PER_TASK': P("cores", default="10"),
                    'BB_SLURM_MAX_RUNNING': P("concurrency", default="170"),
                    'BB_JOBS': P("cores", default="10"),
                    'BB_SLURM_EXCLUSIVE': P("exclusive", default="true"),
                    'BB_SLURM_NODE_IMAGE': P("MASTER_LLVM_ARCHIVE"),
                    'BB_EXPERIMENT_DESCRIPTION': P("experiment-descriptor")
                },
                logEnviron=True),
            steps.MakeDirectory(dir='/run/shm/benchbuild',
                                name='mkdir',
                                description='create benchbuild tmp builddir'),
            cmd("benchbuild", "-vvvv", "run", "-E", "empty", "-P", "auto-stage3",
                name="refresh gentoo stage3 image",
                env={"PATH": P("BB_PATH"),
                     "BB_CONFIG_FILE": P("BB_CONFIG_FILE"),
                     "BB_BUILD_DIR": "/run/shm/benchbuild",
                     "BB_SRC_DIR": P("BB_SRC_DIR"),
                     "BB_TMP_DIR": P("BB_TMP_DIR"),
                     "BB_LLVM_DIR": P("BB_LLVM_DIR")}),
            rmdir("/run/shm/benchbuild",
                  alwaysRun=True),
            cmd("sbatch", "-A", "cl", "-p", "chimaira", P("SLURM_SCRIPT"),
                name="dispatch array job",
                workdir=P("BB_SRC_DIR"),
                env={"PATH": P("BB_PATH")})
        ])))

    # Add experiment builders
    for name in exps:
        c['builders'].append(builder(name, None, accepted_builders,
            factory = BuildFactory([
                trigger(schedulerNames=['trigger-build-jit'],
                        set_properties=exps[name],
                        waitForFinish=True),
                trigger(schedulerNames=['trigger-spawn-chimaira'],
                        set_properties=exps[name],
                        waitForFinish=True)
            ])))

def schedule(c):
    c['schedulers'].append(
        s_trigger("trigger-spawn-chimaira", cb_benchbuild, ["spawn-chimaira"])
    )

    for name in exps:
        c['schedulers'].append(s_trigger("t-{}".format(name), cb_chimaira, [name]))
        c['schedulers'].append(s_force("f-{}".format(name), cb_chimaira, [name]))

register(sys.modules[__name__])
