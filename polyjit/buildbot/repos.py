from buildbot.plugins import *
from buildbot.plugins import util

codebases = {
    'benchbuild': {
        'repository': 'https://github.com/PolyJIT/benchbuild.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'polli': {
        'repository': 'https://github.com/PolyJIT/polli.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'polli-sb': {
        'repository': 'https://github.com/PolyJIT/PolyJIT.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'polly': {
        'repository': 'https://github.com/PolyJIT/polly.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'llvm': {
        'repository': 'https://github.com/PolyJIT/llvm.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'clang': {
        'repository': 'https://github.com/PolyJIT/clang.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'compiler-rt': {
        'repository': 'http://llvm.org/git/compiler-rt.git',
        'branches': ['master', 'release_40'],
        'branch': 'master',
        'revision': None
    },
    'openmp': {
        'repository': 'http://llvm.org/git/openmp.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'stats': {
        'repository': 'https://github.com/simbuerg/pprof-stats.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'isl': {
        'repository': 'https://github.com/simbuerg/isl.git',
        'branches': ['master, isl-0.16.1-cpp'],
        'branch': 'master',
        'revision': None
    },
    'isl-cpp': {
        'repository': 'https://github.com/simbuerg/isl-cpp.git',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'likwid': {
        'repository': 'https://github.com/RRZE-HPC/likwid.git',
        'branches': ['v4.1'],
        'branch': 'v4.1',
        'revision': None
    },
    'vara': {
        'repository': 'git@github.com:vulder/VaRA.git',
        'branch': ['vara-dev', 'vara-dev-jb-buildbot', 'vara-dev-fn'],
        'revision': None
    },
    'vara-llvm': {
        'repository': 'git@github.com:vulder/vara-llvm.git',
        'branch': ['vara-llvm-dev', 'vara-llvm-dev-fn'],
        'revision': None
    },
    'vara-clang': {
        'repository': 'git@github.com:vulder/vara-clang.git',
        'branch': ['vara-clang-dev', 'vara-clang-dev-fn'],
        'revision': None
    },
}

def make_new_cb(bases):
    cb_list = []
    for b in bases:
        cb_list.append(
            util.CodebaseParameter(
                b,
                branch=util.ChoiceStringParameter(
                    name="branch",
                    choices=codebases[b]['branch'],
                    default=codebases[b]['branch'][0]
                ),
                revision=util.FixedParameter(name='revision',
                                             default=''),
                repository=util.FixedParameter(name='repository',
                                               default=codebases[b]['repository']),
                project=util.FixedParameter(name='project', default=b)
            )
        )
    return cb_list

def make_cb(bases):
    b_dict = {}
    for b in bases:
        b_dict[b] = {
            "repository": codebases[b]["repository"],
            "branch": codebases[b]["branch"],
            "revision": codebases[b]["revision"]
        }
    return b_dict


# yapf: disable
def configure(c):
    c['change_source'] = [
        changes.GitPoller(repourl=codebases["benchbuild"]["repository"],
                          workdir='gitpoller-benchbuild',
                          branches=codebases["benchbuild"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli"]["repository"],
                          workdir='gitpoller-polli',
                          branches=codebases["polli"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli-sb"]["repository"],
                          workdir='gitpoller-polli-sb',
                          branches=codebases["polli-sb"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["llvm"]["repository"],
                          workdir='gitpoller-llvm',
                          branches=codebases["llvm"]["branches"],
                          project="llvm",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["clang"]["repository"],
                          workdir='gitpoller-clang',
                          branches=codebases["clang"]["branches"],
                          project="llvm",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polly"]["repository"],
                          workdir='gitpoller-polly',
                          branches=codebases["polly"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["stats"]["repository"],
                          workdir='gitpoller-stats',
                          branches=codebases["stats"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["vara"]["repository"],
                          workdir='gitpoller-vara',
                          branches=codebases["vara"]["branch"],
                          project="vara",
                          pollinterval=3 * 60),
        changes.GitPoller(repourl=codebases["vara-llvm"]["repository"],
                          workdir='gitpoller-vara-llvm',
                          branches=codebases["vara-llvm"]["branch"],
                          project="vara",
                          pollinterval=3 * 60),
        changes.GitPoller(repourl=codebases["vara-clang"]["repository"],
                          workdir='gitpoller-vara-clang',
                          branches=codebases["vara-clang"]["branch"],
                          project="vara",
                          pollinterval=3 * 60)
    ]
# yapf: enable
