from buildbot.plugins import *
from buildbot.plugins import util

codebases = {
    'benchbuild': {
        'repository': 'https://github.com/PolyJIT/benchbuild.git',
        'branch': ['master'],
        'revision': None
    },
    'polli': {
        'repository': 'https://github.com/PolyJIT/polli.git',
        'branch': ['master'],
        'revision': None
    },
    'polli-sb': {
        'repository': 'https://github.com/PolyJIT/PolyJIT.git',
        'branch': ['master'],
        'revision': None
    },
    'polly': {
        'repository': 'https://github.com/PolyJIT/polly.git',
        'branch': ['master'],
        'revision': None
    },
    'llvm': {
        'repository': 'https://github.com/PolyJIT/llvm.git',
        'branch': ['master'],
        'revision': None
    },
    'clang': {
        'repository': 'https://github.com/PolyJIT/clang.git',
        'branch': ['master'],
        'revision': None
    },
    'compiler-rt': {
        'repository': 'http://llvm.org/git/compiler-rt.git',
        'branch': ['master'],
        'revision': None
    },
    'openmp': {
        'repository': 'http://llvm.org/git/openmp.git',
        'branch': ['master'],
        'revision': None
    },
    'stats': {
        'repository': 'https://github.com/simbuerg/pprof-stats.git',
        'branch': ['master'],
        'revision': None
    },
    'isl': {
        'repository': 'https://github.com/simbuerg/isl.git',
        'branch': ['isl-0.16.1-cpp', 'master'],
        'revision': None
    },
    'isl-cpp': {
        'repository': 'https://github.com/simbuerg/isl-cpp.git',
        'branch': ['master'],
        'revision': None
    },
    'likwid': {
        'repository': 'https://github.com/RRZE-HPC/likwid.git',
        'branch': ['v4.1'],
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
        b_dict[b] = codebases[b]
    return b_dict


# yapf: disable
def configure(c):
    c['change_source'] = [
        changes.GitPoller(repourl=codebases["benchbuild"]["repository"],
                          workdir='gitpoller-benchbuild',
                          branches=codebases["benchbuild"]["branch"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli"]["repository"],
                          workdir='gitpoller-polli',
                          branches=codebases["polli"]["branch"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli-sb"]["repository"],
                          workdir='gitpoller-polli-sb',
                          branches=codebases["polli-sb"]["branch"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["llvm"]["repository"],
                          workdir='gitpoller-llvm',
                          branches=codebases["llvm"]["branch"],
                          project="llvm",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["clang"]["repository"],
                          workdir='gitpoller-clang',
                          branches=codebases["clang"]["branch"],
                          project="llvm",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polly"]["repository"],
                          workdir='gitpoller-polly',
                          branches=codebases["polly"]["branch"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["stats"]["repository"],
                          workdir='gitpoller-stats',
                          branches=codebases["stats"]["branch"],
                          project="polyjit",
                          pollinterval=5 * 60)
    ]
# yapf: enable
