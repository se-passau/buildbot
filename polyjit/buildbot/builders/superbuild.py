import sys

from polyjit.buildbot.builders import register
from polyjit.buildbot import slaves
from polyjit.buildbot.utils import (builder, define, git, cmd, ip,
                                    s_abranch, s_dependent, s_force, s_trigger,
                                    hash_upload_to_master,
                                    hash_download_from_master,
                                    clean_unpack, mkdir)
from polyjit.buildbot.repos import make_cb, make_new_cb, codebases
from polyjit.buildbot.master import URL
from buildbot.plugins import util
from buildbot.changes import filter

CODEBASE = make_cb(['polli-sb', 'benchbuild', 'polli'])
FORCE_CODEBASE = make_new_cb(['polli-sb', 'benchbuild', 'polli'])

P = util.Property
BF = util.BuildFactory

ACCEPTED_BUILDERS = \
    slaves.get_hostlist(slaves.infosun,
                        predicate=lambda host: host["host"] in {'debussy', 'ligeti'})


def configure(c):
    sb_steps = [
        define("SUPERBUILD_ROOT", ip("%(prop:builddir)s/polli-sb")),
        define("UCHROOT_SUPERBUILD_ROOT", "/mnt/polli-sb"),
        define("POLYJIT_DEFAULT_BRANCH", "master"),

        git('polli-sb', 'master', codebases, workdir=P("SUPERBUILD_ROOT"),
            mode="full", method="fresh"),
        cmd(ip('%(prop:cmake_prefix)s/bin/cmake'), P("SUPERBUILD_ROOT"),
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_INSTALL_PREFIX=./_install',
            '-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG -DLLVM_ENABLE_STATS',
            '-DBUILD_SHARED_LIBS=Off',
            ip('-DPOLYJIT_BRANCH_CLANG=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
            ip('-DPOLYJIT_BRANCH_LLVM=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
            ip('-DPOLYJIT_BRANCH_POLLI=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
            ip('-DPOLYJIT_BRANCH_POLLY=%(prop:POLYJIT_DEFAULT_BRANCH)s'),
            '-G', 'Ninja',
            usePTY=True,
            name="cmake",
            logEnviron=True,
            description="[uchroot] cmake: release build",
            descriptionDone="[uchroot] configured."),
        cmd("/usr/bin/ninja", "llvm-configure",
            usePTY=True,
            logEnviron=True,
            haltOnFailure=True,
            name="configure LLVM",
            description="configuring LLVM",
            descriptionDone="configured LLVM",
            timeout=4800),
        cmd("/usr/bin/ninja", "polli-configure",
            usePTY=True,
            logEnviron=True,
            haltOnFailure=True,
            name="configure PolyJIT",
            description="configuring PolyJIT",
            descriptionDone="configured PolyJIT",
            timeout=4800),
        cmd("/usr/bin/ninja",
            usePTY=True,
            logEnviron=True,
            haltOnFailure=True,
            name="build jit",
            description="[uchroot] building PolyJIT",
            descriptionDone="[uchroot] built PolyJIT",
            timeout=4800),
        cmd("tar", "czf", "../polyjit_sb.tar.gz", "-C", "./_install", ".")
    ]

    upload_pj = hash_upload_to_master(
        "polyjit_sb.tar.gz",
        "../polyjit_sb.tar.gz",
        "public_html/polyjit_sb.tar.gz", URL)
    sb_steps.extend(upload_pj)

    download_pj = hash_download_from_master("public_html/polyjit_sb.tar.gz",
                                            "polyjit_sb.tar.gz", "polyjit")
    slurm_steps = [
        define("scratch", ip("/scratch/pjtest/sb-%(prop:buildnumber)s/"))
    ]
    slurm_steps.extend(download_pj)
    slurm_steps.extend(clean_unpack("polyjit_sb.tar.gz", "llvm"))
    slurm_steps.extend([
        define("BENCHBUILD_ROOT", ip("%(prop:builddir)s/build/benchbuild/")),
        git('benchbuild', 'master', codebases, workdir=P("BENCHBUILD_ROOT")),
    ])
    slurm_steps.extend([
        define('benchbuild', ip('%(prop:scratch)s/env/bin/benchbuild')),
        define('llvm', ip('%(prop:scratch)s/llvm')),
        define('bb_src', ip('%(prop:scratch)s/benchbuild')),

        cmd('virtualenv', '-ppython3', ip('%(prop:scratch)s/env')),
        cmd(ip('%(prop:scratch)s/env/bin/pip3'), 'install',
            P("BENCHBUILD_ROOT")),
        mkdir(P("scratch")),
        cmd('cp', '-a', ip('%(prop:BENCHBUILD_ROOT)s/dist/benchbuild.pex'),
            P('scratch')),
        cmd("rsync", "-var", "llvm", P("scratch")),
        cmd(P('benchbuild'), 'bootstrap', '-s', env={
            'BB_CONFIG_FILE': '/scratch/pjtest/.benchbuild.json',
            'BB_TMP_DIR': '/scratch/pjtest/src/',
            'BB_TEST_DIR': P("testinputs"),
            'BB_GENTOO_AUTOTEST_LOC': '/scratch/pjtest/gentoo-autotest',
            'BB_SLURM_PARTITION': 'anywhere',
            'BB_SLURM_NODE_DIR': '/local/hdd/buildbot-polyjit/',
            'BB_SLURM_ACCOUNT': 'anywhere',
            'BB_SLURM_TIMELIMIT': '24:00:00',
            'BB_CONTAINER_MOUNTS': ip('["%(prop:llvm)s", "%(prop:bb_src)s"]'),
            'BB_CONTAINER_PREFIXES': '["/opt/benchbuild", "/", "/usr", "/usr/local"]',
            'BB_ENV_PATH':
                ip('["%(prop:llvm)s/bin", "/scratch/pjtest/erlent/build"]'),
            'BB_ENV_LD_LIBRARY_PATH':
                ip('["%(prop:llvm)s/lib", "/scratch/pjtest/erlent/build"]'),
            'BB_LLVM_DIR': ip('%(prop:scratch)s/llvm'),
            'BB_LIKWID_PREFIX': '/usr',
            'BB_PAPI_INCLUDE': '/usr/include',
            'BB_PAPI_LIBRARY': '/usr/lib',
            'BB_SRC_DIR': ip('%(prop:bb_src)s'),
            'BB_SLURM_LOGS': ip('%(prop:scratch)s/slurm.log'),
            'BB_UNIONFS_ENABLE': 'false'
            },
            workdir=P('scratch')),
        # This only works on infosun machines
        cmd("ln", "-s", ip("/scratch/pjtest/benchbuild-src/"),
            ip("%(prop:bb_src)s")),
        mkdir(ip("%(prop:scratch)s/results"))
    ])

    c['builders'].append(
        builder("polyjit-superbuild", None,
                ACCEPTED_BUILDERS, tags=['polyjit'],
                collapseRequests=True,
                factory=BF(sb_steps)))
    c['builders'].append(
        builder("polyjit-superbuild-slurm", None,
                ACCEPTED_BUILDERS, tags=['polyjit'],
                collapseRequests=True,
                factory=BF(slurm_steps)))


def schedule(c):
    superbuild_sched = s_abranch("bs_polyjit-superbuild",
                                 CODEBASE, ["polyjit-superbuild"],
                                 treeStableTimer=10 * 60)
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
