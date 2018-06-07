from collections import OrderedDict
from functools import partial
import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, ip,
                                    s_abranch, s_dependent, s_force, s_trigger,
                                    hash_upload_to_master,
                                    hash_download_from_master,
                                    clean_unpack, mkdir)
from polyjit.buildbot.repos import make_cb, make_force_cb
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

P = util.Property
BF = util.BuildFactory

ACCEPTED_BUILDERS = \
    slaves.get_hostlist(slaves.infosun,
                        predicate=lambda host: host["host"] in {'debussy', 'ligeti'})

BB_ENV = {
    'BB_CONFIG_FILE': '/scratch/pjtest/.benchbuild.json',
    'BB_TMP_DIR': '/scratch/pjtest/src/',
    'BB_TEST_DIR': P("testinputs"),
    'BB_GENTOO_AUTOTEST_LOC': '/scratch/pjtest/gentoo-autotest',
    'BB_SLURM_PARTITION': 'anywhere',
    'BB_SLURM_NODE_DIR': '/local/hdd/buildbot-polyjit/',
    'BB_SLURM_ACCOUNT': 'anywhere',
    'BB_SLURM_TIMELIMIT': '24:00:00',
    'BB_CONTAINER_MOUNTS': ip('["%(prop:llvm)s", "%(prop:bb_src)s"]'),
    'BB_CONTAINER_PREFIXES':
        '["/opt/benchbuild", '
        '"/", '
        '"/usr", '
        '"/usr/local"]',
    'BB_ENV_PATH':
        ip('["/scratch/pjtest/opt/papi-5.5.1/install/bin", '
            '"%(prop:llvm)s/bin", '
            '"%(prop:llvm_prefix)s/bin", '
            '"/scratch/pjtest/erlent/build"]'),
    'BB_ENV_LD_LIBRARY_PATH':
        ip('["/scratch/pjtest/opt/papi-5.5.1/install/lib", '
            '"%(prop:llvm)s/lib", '
            '"%(prop:llvm_libs)s", '
            '"/scratch/pjtest/erlent/build"]'),
    'BB_LLVM_DIR': ip('%(prop:scratch)s/llvm'),
    'BB_LIKWID_PREFIX': '/usr',
    'BB_PAPI_INCLUDE': '/usr/include',
    'BB_PAPI_LIBRARY': '/usr/lib',
    'BB_SRC_DIR': ip('%(prop:bb_src)s'),
    'BB_SLURM_LOGS': ip('%(prop:scratch)s/slurm.log'),
    'BB_UNIONFS_ENABLE': 'false'
}

REPOS = OrderedDict()
REPOS['pjit-benchbuild'] = {
    'repository': 'https://github.com/PolyJIT/benchbuild',
    'branch': 'master',
    'default_branch': 'master',
    'revision': None
}
REPOS['pjit-polli-sb'] = {
    'repository': 'https://github.com/PolyJIT/PolyJIT',
    'branch': 'master',
    'default_branch': 'master',
    'revision': None
}
REPOS['pjit-polli-sb'] = {
    'repository': 'https://github.com/PolyJIT/polli',
    'default_branch': 'master',
    'branch': 'master',
    'revision': None
}

CODEBASE = make_cb(REPOS)
FORCE_CODEBASE = make_force_cb(REPOS)


def icmd(*args, **kwargs):
    ip_list = [ ip(le) if isinstance(le, str) else le for le in args]
    return cmd(*ip_list, **kwargs)

ICMD_P = partial(icmd,
    usePTY=True,
    env={"LD_LIBRARY_PATH": P("llvm_libs")},
    logEnviron=True)

CMD_P = partial(cmd,
    usePTY=True,
    env={"LD_LIBRARY_PATH": P("llvm_libs")},
    logEnviron=True,
    haltOnFailure=True,
    timeout=4800)


def configure(c):
    sb_steps = [
        define("SUPERBUILD_ROOT", ip("%(prop:builddir)s/polli-sb")),
        define("POLYJIT_DEFAULT_BRANCH", "master"),

        git('pjit-polli-sb', 'master', REPOS, workdir=P("SUPERBUILD_ROOT"),
            mode="full", method="fresh"),
        ICMD_P('%(prop:cmake_prefix)s/bin/cmake', P("SUPERBUILD_ROOT"),
               '-DCMAKE_CXX_COMPILER=%(prop:cxx)s',
               '-DCMAKE_C_COMPILER=%(prop:cc)s',
               '-DCMAKE_BUILD_TYPE=Release',
               '-DCMAKE_INSTALL_PREFIX=./_install',
               '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
               '-DBUILD_SHARED_LIBS=Off',
               '-DPOLYJIT_PAPI_PREFIX=/scratch/pjtest/opt/papi-5.5.1/install',
               '-DPOLYJIT_BRANCH_CLANG=%(prop:POLYJIT_DEFAULT_BRANCH)s',
               '-DPOLYJIT_BRANCH_LLVM=%(prop:POLYJIT_DEFAULT_BRANCH)s',
               '-DPOLYJIT_BRANCH_POLLI=%(prop:POLYJIT_DEFAULT_BRANCH)s',
               '-DPOLYJIT_BRANCH_POLLY=%(prop:POLYJIT_DEFAULT_BRANCH)s',
               '-G', 'Ninja',
               name="cmake",
               description="[uchroot] cmake: release build",
               descriptionDone="[uchroot] configured."),
        CMD_P("/usr/bin/ninja", "llvm-configure",
              name="configure LLVM",
              description="configuring LLVM",
              descriptionDone="configured LLVM"),
        CMD_P("/usr/bin/ninja", "polli-configure",
              name="configure PolyJIT",
              description="configuring PolyJIT",
              descriptionDone="configured PolyJIT"),
        CMD_P("/usr/bin/ninja",
              name="build jit",
              description="[uchroot] building PolyJIT",
              descriptionDone="[uchroot] built PolyJIT"),
        cmd("tar", "czf", "../polyjit_sb.tar.gz", "-C", "./_install", ".")
    ]

    sb_steps.extend(hash_upload_to_master(
        "polyjit_sb.tar.gz",
        "../polyjit_sb.tar.gz",
        "public_html/polyjit_sb.tar.gz", URL))

    slurm_steps = [
        define("scratch", ip("/scratch/pjtest/sb-%(prop:buildnumber)s/")),
        *hash_download_from_master("public_html/polyjit_sb.tar.gz", "polyjit_sb.tar.gz", "polyjit"),
        *clean_unpack("polyjit_sb.tar.gz", "llvm"),
        define("BENCHBUILD_ROOT", ip("%(prop:builddir)s/build/benchbuild/")),
        git('pjit-benchbuild', 'master', REPOS, workdir=P("BENCHBUILD_ROOT")),
        define('benchbuild', ip('%(prop:scratch)s/env/bin/benchbuild')),
        define('llvm', ip('%(prop:scratch)s/llvm')),
        define('bb_src', ip('%(prop:scratch)s/benchbuild')),
        icmd('virtualenv', '-ppython3', '%(prop:scratch)s/env'),
        icmd('%(prop:scratch)s/env/bin/pip3', 'install', P("BENCHBUILD_ROOT")),
        mkdir(P("scratch")),
        cmd("rsync", "-var", "llvm", P("scratch")),
        cmd(P('benchbuild'), 'bootstrap', '-s', logEnviron=True, env=BB_ENV, workdir=P('scratch')),
        # This only works on infosun machines
        icmd("ln", "-s", "/scratch/pjtest/benchbuild-src/", "%(prop:bb_src)s"),
        mkdir(ip("%(prop:scratch)s/results"))
    ]

    c['builders'].extend([
        builder("polyjit-superbuild", None,
                ACCEPTED_BUILDERS, tags=['polyjit'],
                collapseRequests=True,
                factory=BF(sb_steps)),
        builder("polyjit-superbuild-slurm", None,
                ACCEPTED_BUILDERS, tags=['polyjit'],
                collapseRequests=True,
                factory=BF(slurm_steps))
    ])


def schedule(c):
    superbuild_sched = s_abranch("bs_polyjit-superbuild",
                                 CODEBASE, ["polyjit-superbuild"],
                                 treeStableTimer=2 * 60)
    c['schedulers'].extend([
        superbuild_sched,
        s_force("fs_polyjit-superbuild", FORCE_CODEBASE,
                ["polyjit-superbuild"]),
        s_trigger("ts_polyjit-superbuild", CODEBASE,
                  ["polyjit-superbuild"]),

        s_dependent("ds_polyjit-superbuild-slurm",
                    superbuild_sched,
                    ["polyjit-superbuild-slurm"]),
        s_force("fs_polyjit-superbuild-slurm", FORCE_CODEBASE,
                ["polyjit-superbuild-slurm"])
    ])


register(sys.modules[__name__])
