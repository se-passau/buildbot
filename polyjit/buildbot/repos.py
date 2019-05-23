from buildbot.plugins import *
from buildbot.plugins import util

codebases = {
    'pjit-benchbuild': {
        'repository': 'https://github.com/PolyJIT/benchbuild',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'pjit-polli': {
        'repository': 'https://github.com/PolyJIT/polli',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'pjit-polli-sb': {
        'repository': 'https://github.com/PolyJIT/PolyJIT',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'polly': {
        'repository': 'https://github.com/PolyJIT/polly',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'llvm': {
        'repository': 'https://github.com/PolyJIT/llvm',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'clang': {
        'repository': 'https://github.com/PolyJIT/clang',
        'branches': ['master'],
        'branch': 'master',
        'revision': None
    },
    'compiler-rt': {
        'repository': 'https://llvm.org/git/compiler-rt.git',
        'branches': ['master', 'release_70', 'release_80'],
        'branch': 'master',
        'revision': None
    },
    'clang-tools-extra': {
        'repository': 'https://git.llvm.org/git/clang-tools-extra.git/',
        'branches': ['master', 'release_70', 'release_80'],
        'branch': 'master',
        'revision': None
    },
    'phasar': {
        'repository': 'https://github.com/secure-software-engineering/phasar.git',
        'branches': ['master', 'development'],
        'branch': 'master',
        'revision': None
    },
    'vara': {
        'repository': 'https://github.com/se-passau/VaRA',
        'repository_clone_url': 'git@github.com:se-passau/VaRA',
        'branches': ['vara-dev'],
        'revision': None
    },
    'vara-llvm': {
        'repository': 'https://github.com/se-passau/vara-llvm',
        'repository_clone_url': 'git@github.com:se-passau/vara-llvm',
        'branches': ['vara-80-dev'],
        'revision': None
    },
    'vara-clang': {
        'repository': 'https://github.com/se-passau/vara-clang',
        'repository_clone_url': 'git@github.com:se-passau/vara-clang',
        'branches': ['vara-80-dev'],
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
    return

# yapf: enable
