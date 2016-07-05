from buildbot.plugins import *

codebases = {
    'benchbuild': {'repository': 'https://github.com/PolyJIT/benchbuild.git',
                   'branches': ['master', 'develop', 'perf']},
    'stats': {'repository': 'https://github.com/simbuerg/pprof-stats.git',
              'branches': ['master']},
    'polli': {'repository': 'https://github.com/PolyJIT/polli.git',
              'branches': ['master', 'next', 'perf']},
    'polli-simbuerg': {'repository': 'https://github.com/simbuerg/polli.git',
                       'branches': ['master', 'next', 'perf']},
    'llvm': {'repository': 'http://llvm.org/git/llvm.git',
             'branches': ['master']},
    'clang': {'repository': 'http://llvm.org/git/clang.git',
              'branches': ['master']},
    'polly-up': {'repository': 'http://llvm.org/git/polly.git',
                 'branches': ['master']},
    'polly': {'repository': 'git://github.com/simbuerg/polly.git',
              'branches': ['master']},
    'libcxx': {'repository': 'http://llvm.org/git/libcxx.git',
               'branches': ['master']},
    'libcxx_abi': {'repository': 'http://llvm.org/git/libcxxabi.git',
                   'branches': ['master']},
    'openmp': {'repository': 'http://llvm.org/git/openmp.git',
               'branches': ['master']},
}


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
                          branches=codebases["benchbuild"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli"]["repository"],
                          workdir='gitpoller-polli',
                          branches=codebases["polli"]["branches"],
                          project="polyjit",
                          pollinterval=5 * 60),
        changes.GitPoller(repourl=codebases["polli-simbuerg"]["repository"],
                          workdir='gitpoller-polli-simbuerg',
                          branches=codebases["polli-simbuerg"]["branches"],
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
                          pollinterval=5 * 60)
    ]
# yapf: enable
