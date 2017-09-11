__all__ = ["jit", "llvm", "slurm", "superbuild", "vara", "varafeatures"]
__ALL__ = []


def register(builder):
    __ALL__.append(builder)


def configure(master_config):
    for b in __ALL__:
        b.configure(master_config)


def schedule(master_config):
    for b in __ALL__:
        b.schedule(master_config)
