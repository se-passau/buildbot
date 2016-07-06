from buildbot.plugins import *

codebases = {
    'benchbuild': {'repository': 'https://github.com/PolyJIT/benchbuild.git',
                   'branches': ['master', 'develop', 'perf']},
    'polli': {'repository': 'https://github.com/PolyJIT/polli.git',
              'branches': ['master', 'next', 'perf']},
    'polly': {'repository': 'git://github.com/PolyJIT/polly.git',
              'branches': ['devel']},
    'llvm': {'repository': 'https://github.com/PolyJIT/llvm.git',
             'branches': ['master']},
    'clang': {'repository': 'http://llvm.org/git/clang.git',
              'branches': ['master']},
    'compiler-rt': {'repository': 'http://llvm.org/git/compiler-rt.git',
                    'branches': ['master']},
    'openmp': {'repository': 'http://llvm.org/git/openmp.git',
               'branches': ['master']},
    'stats': {'repository': 'https://github.com/simbuerg/pprof-stats.git',
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
