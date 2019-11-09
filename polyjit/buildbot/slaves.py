from buildbot.plugins import worker

infosun = {
    "bayreuther01": {
        "host": "bayreuther01",
        "password": None,
        "properties": {
            "uchroot_image_path": "/local/hdd/buildbot/disco-image/",
            "uchroot_binary": "/local/hdd/buildbot/erlent/build/uchroot",
            "has_munged": True,
            "can_build_llvm_debug": True
        }
    },
    "bayreuther02": {
        "host": "bayreuther02",
        "password": None,
        "properties": {
            "uchroot_image_path": "/local/hdd/buildbot/disco-image/",
            "uchroot_binary": "/local/hdd/buildbot/erlent/build/uchroot",
            "has_munged": True,
            "can_build_llvm_debug": True
        }
    }
}

def get_hostlist(slave_dict, predicate = None):
    if not predicate:
        predicate = lambda x : True
    hosts = []
    for k in slave_dict:
        if predicate(slave_dict[k]):
            hosts.append(slave_dict[k]["host"])
    return hosts


def configure(c):
    for k in infosun:
        slave = infosun[k]
        props = {}
        if "properties" in slave:
            props = slave["properties"]
        c['workers'].append(worker.Worker(slave["host"], slave[
            "password"], properties = props))
