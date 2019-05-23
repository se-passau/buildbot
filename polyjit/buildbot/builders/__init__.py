__all__ = ["superbuild", "vara_master_dev", "vara_master_opt", "vara_feature_dev", "vara_feature_opt", "vara_phasar_master_dev"]
__ALL__ = []


def register(builder):
    __ALL__.append(builder)


def configure(master_config):
    for b in __ALL__:
        b.configure(master_config)


def schedule(master_config):
    for b in __ALL__:
        b.schedule(master_config)
