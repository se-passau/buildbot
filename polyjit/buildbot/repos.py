from buildbot.plugins import *
from buildbot.plugins import util

codebases = {
    'benchbuild': {'repository': 'https://github.com/PolyJIT/benchbuild.git',
                   'branch': ['master', 'develop', 'perf']},
    'polli': {'repository': 'https://github.com/PolyJIT/polli.git',
              'branch': ['master', 'next', 'perf']},
    'polly': {'repository': 'git://github.com/PolyJIT/polly.git',
              'branch': ['devel']},
    'llvm': {'repository': 'https://github.com/PolyJIT/llvm.git',
             'branch': ['master']},
    'clang': {'repository': 'http://github.com/PolyJIT/clang.git',
              'branch': ['master']},
    'compiler-rt': {'repository': 'http://llvm.org/git/compiler-rt.git',
                    'branch': ['master']},
    'openmp': {'repository': 'http://llvm.org/git/openmp.git',
               'branch': ['master']},
    'stats': {'repository': 'https://github.com/simbuerg/pprof-stats.git',
              'branch': ['master']},
    'isl' : {'repository': 'https://github.com/simbuerg/isl.git',
             'branch': ['master', 'isl-0.16.1-cpp']},
    'isl-cpp': {'repository': 'https://github.com/simbuerg/isl-cpp.git',
                'branch': ['master']},
    'likwid': {'repository': 'https://github.com/RRZE-HPC/likwid.git',
                'branch': ['v4.1']},
}

def make_new_cb(bases):
    cb_list = []
    for b in bases:
        cb_list.append(
            util.CodebaseParameter(
                "",
                name=b,
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
