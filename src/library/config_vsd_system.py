#!/usr/bin/env python

from ansible.module_utils.basic import AnsibleModule
import importlib
from bambou import exceptions

VSPK = None

DOCUMENTATION = '''
---
module: config_vsd_system
short_description: Update/configure VSD System parameters
options:
  vsd_auth:
    description:
      - VSD credentials to access VSD GUI
    required: true
    default: null
  vsd_version:
    description:
      - VSD version
    required: true
    default: null
  gateway_purge_time:
    description:
      - Increase or decrease timeout value in VSD
    default: null
  get_gateway_purge_time:
    decription:
      - Get the current gateway purge tiem set
    default: False
    choices: [ True, False ]

'''

EXAMPLES = '''
# Configure gateway purge time in VSD
- config_vsd_system:
    vsd_auth:
      username: csproot
      password: csproot
      enterprise: csp
      api_url: https://10.0.0.10:8443
    vsd_version: "5.4.1"
    gateway_purge_time: 7003

- config_vsd_system:
    vsd_auth:
      username: csproot
      password: csproot
      enterprise: csp
      api_url: https://10.0.0.10:8443
    vsd_version: "5.4.1"
    get_gateway_purge_time: True
'''


def format_api_version(version):
    if version.startswith('3'):
        return ('v3_2')
    elif version.startswith('6'):
        return ('v' + version[0])
    elif version.startswith('20'):
        return ('v6')
    else:
        return ('v' + version[0] + '_0')


def get_vsd_session(vsd_auth, vsd_version):
    version = format_api_version(vsd_version)

    global VSPK
    VSPK = importlib.import_module('vspk.{0:s}'.format(version))

    session = VSPK.NUVSDSession(**vsd_auth)
    session.start()
    csproot = session.user
    return csproot


def set_gateway_purge_time(csproot, gw_purge_time):
    sys_config = csproot.system_configs.get_first()
    sys_config.ad_gateway_purge_time = int(gw_purge_time)
    sys_config.save()


def get_gateway_purge_time_value(csproot):
    sys_config = csproot.system_configs.get_first()
    purge_val = sys_config.ad_gateway_purge_time

    return purge_val


def main():
    arg_spec = dict(
        vsd_auth=dict(required=True, type='dict'),
        get_gateway_purge_time=dict(default=False, type='bool'),
        gateway_purge_time=dict(type='int')
    )
    module = AnsibleModule(argument_spec=arg_spec, supports_check_mode=True)

    vsd_auth = module.params['vsd_auth']
    vsd_version = module.params['vsd_version']
    gw_purge_time = module.params['gateway_purge_time']
    get_gateway_purge_time = module.params['get_gateway_purge_time']

    try:
        csproot = get_vsd_session(vsd_auth, vsd_version)
    except ImportError:
        module.fail_json(msg="vspk is required for this module, or "
                         "API version specified does not exist.")
        return
    except Exception as e:
        module.fail_json(msg="Could not establish connection to VSD %s" % e)
        return

    if not get_gateway_purge_time:
        try:
            set_gateway_purge_time(csproot, gw_purge_time)
        except exceptions.BambouHTTPError as e:
            if "There are no attribute changes" in str(e):
                module.exit_json(changed=True, result="Gateway time is already"
                                 " updated to %s" % int(gw_purge_time))
                return
        except Exception as e:
            module.fail_json(
                msg="Could not update gateway purge timer : %s" % e)
            return

        module.exit_json(
            changed=True,
            result="Gateway purge time set to %ssec" % gw_purge_time)

    else:
        try:
            purge_val = get_gateway_purge_time_value(csproot)
        except Exception as e:
            module.fail_json(msg="Could not retrieve "
                             "gateway purge timer : %s" % e)
            return

        module.exit_json(changed=True, result=purge_val)


# Run the main

if __name__ == '__main__':
    main()
