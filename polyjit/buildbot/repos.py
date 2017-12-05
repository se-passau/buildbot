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
        'branches': ['master', 'release_50'],
        'branch': 'master',
        'revision': None
    },
    'clang-tools-extra': {
        'repository': 'https://git.llvm.org/git/clang-tools-extra.git/',
        'branches': ['master', 'release_50'],
        'branch': 'master',
        'revision': None
    },
    'vara': {
        'repository': 'git@github.com:vulder/VaRA.git',
        'branches': ['vara-dev'],
        'revision': None
    },
    'vara-llvm': {
        'repository': 'git@github.com:vulder/vara-llvm.git',
        'branches': ['vara-llvm-50-dev'],
        'revision': None
    },
    'vara-clang': {
        'repository': 'git@github.com:vulder/vara-clang.git',
        'branches': ['vara-clang-50-dev'],
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
                    choices=codebases[b]['branches'],
                    default=codebases[b]['branches'][0]
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


def make_git_cb(bases):
    b_dict = {}
    for b in bases:
        b_dict[b] = {
            'repository' : codebases[b]['repository'],
            'branch' : bases[b]['default_branch'],
            'revision' : codebases[b]['revision']
        }
    return b_dict;


def make_force_cb(bases):
    cb_list = []
    for b in bases:
        cb_list.append(
            util.CodebaseParameter(
                b,
                branch=util.ChoiceStringParameter(
                    name="branch",
                    choices=codebases[b]['branches'],
                    default=bases[b]['default_branch']
                ),
                revision=util.FixedParameter(name='revision',
                                             default=''),
                repository=util.FixedParameter(name='repository',
                                               default=codebases[b]['repository']),
                project=util.FixedParameter(name='project', default=b)
            )
        )
    return cb_list


# yapf: disable
def configure(c):
    c['change_source'] = [
        changes.GitPoller(repourl=codebases["vara"]["repository"],
                          workdir='gitpoller-vara',
                          branches=lambda x: True,
                          project="vara",
                          pollinterval=3 * 60),
        changes.GitPoller(repourl=codebases["vara-llvm"]["repository"],
                          workdir='gitpoller-vara-llvm',
                          branches=lambda x: True,
                          project="vara",
                          pollinterval=3 * 60),
        changes.GitPoller(repourl=codebases["vara-clang"]["repository"],
                          workdir='gitpoller-vara-clang',
                          branches=lambda x: True,
                          project="vara",
                          pollinterval=3 * 60)
    ]
# yapf: enable
