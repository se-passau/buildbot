from buildbot.plugins import *

infosun = {
    "polyjit-ci": {
        "host": "polyjit-ci",
        "password": None,
        "properties" : {
            "uchroot_image_path": "/data/polyjit/trusty-image/",
            "uchroot_binary": "/data/polyjit/erlent/build/uchroot"
        }
    },
    "local": {
        "host": "local",
        "password": None,
        "properties" : {
            "uchroot_image_path": "/dock/buildbot/trusty-image/",
            "uchroot_binary": "/dock/buildbot/erlent/build/uchroot"
        }
    },
    "ivy-vm": {
        "host": "ivy-vm",
        "password": None,
        "properties" : {
            "uchroot_image_path": "/buildbot/trusty-image/",
            "uchroot_binary": "/buildbot/erlent/build/uchroot"
        }
    }
}


def get_hostlist(slave_dict):
    hosts = []
    for k in slave_dict:
        hosts.append(infosun[k]["host"])
    return hosts


def configure(c):
    for k in infosun:
        slave = infosun[k]
        props = {}
        if "properties" in slave:
            props = slave["properties"]
        c['slaves'].append(buildslave.BuildSlave(slave["host"], slave[
            "password"], properties = props))
