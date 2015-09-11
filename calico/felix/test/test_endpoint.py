# -*- coding: utf-8 -*-
# Copyright 2014, 2015 Metaswitch Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
felix.test.test_endpoint
~~~~~~~~~~~~~~~~~~~~~~~~

Tests of endpoint module.
"""
import gevent
import logging
import itertools
from contextlib import nested
from calico.felix.endpoint import EndpointManager
from calico.felix.fiptables import IptablesUpdater
from calico.felix.dispatch import DispatchChains
from calico.felix.profilerules import RulesManager
from gevent.event import AsyncResult

import mock
from mock import Mock, MagicMock, patch

from calico.felix.actor import actor_message, ResultOrExc, SplitBatchAndRetry
from calico.felix.test.base import BaseTestCase
from calico.felix.test import stub_utils
from calico.felix import config
from calico.felix import devices
from calico.felix import endpoint
from calico.felix import futils
from calico.datamodel_v1 import EndpointId

_log = logging.getLogger(__name__)


class TestLocalEndpoint(BaseTestCase):
    def setUp(self):
        super(TestLocalEndpoint, self).setUp()
        self.m_config = Mock(spec=config.Config)
        self.m_config.IFACE_PREFIX = "tap"
        self.m_config.POLICY_ONLY = False
        self.m_iptables_updater = Mock(spec=IptablesUpdater)
        self.m_dispatch_chains = Mock(spec=DispatchChains)
        self.m_rules_mgr = Mock(spec=RulesManager)

    def get_local_endpoint(self, combined_id, ip_type):
        local_endpoint = endpoint.LocalEndpoint(self.m_config,
                                                combined_id,
                                                ip_type,
                                                self.m_iptables_updater,
                                                self.m_dispatch_chains,
                                                self.m_rules_mgr)

        # For purposes of our testing, we force things to happen in line.
        local_endpoint.greenlet = gevent.getcurrent()
        return local_endpoint

    def test_on_endpoint_update_v4(self):
        combined_id = EndpointId("host_id", "orchestrator_id",
                                 "workload_id", "endpoint_id")
        ip_type = futils.IPV4
        retcode = futils.CommandOutput("", "")
        local_ep = self.get_local_endpoint(combined_id, ip_type)

        # Call with no data; should be ignored (no configuration to remove).
        local_ep.on_endpoint_update(None, async=False)

        ips = ["1.2.3.4"]
        iface = "tapabcdef"
        data = { 'endpoint': "endpoint_id",
                 'mac': stub_utils.get_mac(),
                 'name': iface,
                 'ipv4_nets': ips,
                 'profile_ids': []}

        # Report an initial update (endpoint creation) and check configured
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv4'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv4.assert_called_once_with(iface)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=True)

        # Send through an update with no changes - should redo without
        # resetting ARP.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv4'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv4.assert_called_once_with(iface)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)

        # Change the MAC address and try again, leading to reset of ARP.
        data['mac'] = stub_utils.get_mac()
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv4'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv4.assert_called_once_with(iface)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=True)

        # Send empty data, which deletes the endpoint.
        with mock.patch('calico.felix.devices.set_routes'):
            local_ep.on_endpoint_update(None, async=False)
            devices.set_routes.assert_called_once_with(ip_type, set(),
                                                       data["name"], None)

    def test_on_endpoint_update_v6(self):
        combined_id = EndpointId("host_id", "orchestrator_id",
                                 "workload_id", "endpoint_id")
        ip_type = futils.IPV6
        retcode = futils.CommandOutput("", "")
        local_ep = self.get_local_endpoint(combined_id, ip_type)

        # Call with no data; should be ignored (no configuration to remove).
        local_ep.on_endpoint_update(None, async=False)

        ips = ["2001::abcd"]
        gway = "2020:ab::9876"
        iface = "tapabcdef"
        data = { 'endpoint': "endpoint_id",
                 'mac': stub_utils.get_mac(),
                 'name': iface,
                 'ipv6_nets': ips,
                 'ipv6_gateway': gway,
                 'profile_ids': []}

        # Report an initial update (endpoint creation) and check configured
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv6'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv6.assert_called_once_with(iface,
                                                                         gway)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)

        # Send through an update with no changes - should redo without
        # resetting ARP.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv6'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv6.assert_called_once_with(iface,
                                                                         gway)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)

        # Send through an update with no changes - would reset ARP, but this is
        # IPv6 so it won't.
        data['mac'] = stub_utils.get_mac()
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv6'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv6.assert_called_once_with(iface,
                                                                         gway)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)

        # Send empty data, which deletes the endpoint.
        with mock.patch('calico.felix.devices.set_routes'):
            local_ep.on_endpoint_update(None, async=False)
            devices.set_routes.assert_called_once_with(ip_type, set(),
                                                       data["name"], None)

    def test_on_interface_update_v4(self):
        combined_id = EndpointId("host_id", "orchestrator_id",
                                 "workload_id", "endpoint_id")
        ip_type = futils.IPV4
        retcode = futils.CommandOutput("", "")
        local_ep = self.get_local_endpoint(combined_id, ip_type)

        ips = ["1.2.3.4"]
        iface = "tapabcdef"
        data = { 'endpoint': "endpoint_id",
                 'mac': stub_utils.get_mac(),
                 'name': iface,
                 'ipv4_nets': ips,
                 'profile_ids': []}

        # We can only get on_interface_update calls after the first
        # on_endpoint_update, so trigger that.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv4'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv4.assert_called_once_with(iface)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=True)

        # Now pretend to get an interface update - does all the same work.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv4'):
                local_ep.on_interface_update()
                devices.configure_interface_ipv4.assert_called_once_with(iface)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=True)

    def test_on_interface_update_v6(self):
        combined_id = EndpointId("host_id", "orchestrator_id",
                                 "workload_id", "endpoint_id")
        ip_type = futils.IPV6
        retcode = futils.CommandOutput("", "")
        local_ep = self.get_local_endpoint(combined_id, ip_type)

        ips = ["1234::5678"]
        iface = "tapabcdef"
        data = { 'endpoint': "endpoint_id",
                 'mac': stub_utils.get_mac(),
                 'name': iface,
                 'ipv6_nets': ips,
                 'profile_ids': []}

        # We can only get on_interface_update calls after the first
        # on_endpoint_update, so trigger that.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv6'):
                local_ep.on_endpoint_update(data, async=False)
                self.assertEqual(local_ep._mac, data['mac'])
                devices.configure_interface_ipv6.assert_called_once_with(iface,
                                                                         None)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)

        # Now pretend to get an interface update - does all the same work.
        with mock.patch('calico.felix.devices.set_routes'):
            with mock.patch('calico.felix.devices.configure_interface_ipv6'):
                local_ep.on_interface_update()
                devices.configure_interface_ipv6.assert_called_once_with(iface,
                                                                         None)
                devices.set_routes.assert_called_once_with(ip_type,
                                                           set(ips),
                                                           iface,
                                                           data['mac'],
                                                           reset_arp=False)


class TestEndpoint(BaseTestCase):
    def test_get_endpoint_rules(self):
        to_pfx = '--append felix-to-abcd'
        from_pfx = '--append felix-from-abcd'
        expected_result = (
            {
                'felix-from-abcd': 
                [
                    # Always start with a 0 MARK.
                    from_pfx + ' --jump MARK --set-mark 0',
                    # From chain polices the MAC address.
                    from_pfx + ' --match mac ! --mac-source aa:22:33:44:55:66 '
                               '--jump DROP --match comment --comment '
                               '"Incorrect source MAC"',

                    # Jump to the first profile.
                    from_pfx + ' --jump felix-p-prof-1-o',
                    # Short-circuit: return if the first profile matched.
                    from_pfx + ' --match mark --mark 1/1 --match comment '
                               '--comment "Profile accepted packet" '
                               '--jump RETURN',

                    # Jump to second profile.
                    from_pfx + ' --jump felix-p-prof-2-o',
                    # Return if the second profile matched.
                    from_pfx + ' --match mark --mark 1/1 --match comment '
                               '--comment "Profile accepted packet" '
                               '--jump RETURN',

                    # Drop the packet if nothing matched.
                    from_pfx + ' --jump DROP -m comment --comment '
                               '"Default DROP if no match (endpoint e1):"'
                ],
                'felix-to-abcd': 
                [
                    # Always start with a 0 MARK.
                    to_pfx + ' --jump MARK --set-mark 0',

                    # Jump to first profile and return iff it matched.
                    to_pfx + ' --jump felix-p-prof-1-i',
                    to_pfx + ' --match mark --mark 1/1 --match comment '
                             '--comment "Profile accepted packet" '
                             '--jump RETURN',

                    # Jump to second profile and return iff it matched.
                    to_pfx + ' --jump felix-p-prof-2-i',
                    to_pfx + ' --match mark --mark 1/1 --match comment '
                             '--comment "Profile accepted packet" '
                             '--jump RETURN',

                    # Drop anything that doesn't match.
                    to_pfx + ' --jump DROP -m comment --comment '
                             '"Default DROP if no match (endpoint e1):"'
                ]
            },
            {
                # From chain depends on the outbound profiles.
                'felix-from-abcd': set(['felix-p-prof-1-o',
                                        'felix-p-prof-2-o']),
                # To chain depends on the inbound profiles.
                'felix-to-abcd': set(['felix-p-prof-1-i',
                                      'felix-p-prof-2-i'])
            }
        )
        result = endpoint._get_endpoint_rules("e1", "abcd",
                                              "aa:22:33:44:55:66",
                                              ["prof-1", "prof-2"])

        # Log the whole diff if the comparison fails.
        self.maxDiff = None
        self.assertEqual(result, expected_result)