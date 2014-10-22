#!/usr/bin/python
#
# Nagios plugin to check openstack nova
#
# Please change SOURCE_FILE to the path of your keystonerc
# Note that we expect the admin user to be in all but service tenant
#
# Please change SOURCE_FILE to the path of your keystonerc
# Note that we expect the admin user to be in all but service tenant
#
# Copyright 2014 ETH Zurich, ISGINF, Bastian Ballmann
# E-Mail: bastian.ballmann@inf.ethz.ch
# Web: http://www.isg.inf.ethz.ch
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.


###[ Loading modules ]###

import os
import subprocess
import sys
import novaclient.v1_1.client as nova_client
import keystoneclient.v2_0.client as keystone_client


###[ Configuration ]###

SOURCE_FILE = "/etc/nagios/keystonerc"


###[ MAIN PART ]###

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

# Source keystonerc file
command = ['bash', '-c', 'source ' + SOURCE_FILE + ' && env']
proc = subprocess.Popen(command, stdout = subprocess.PIPE)

for line in proc.stdout:
  (key, _, value) = line.partition("=")
  os.environ[key] = value.rstrip("\n")

proc.communicate()

# Count all vms of all tenants
try:
  keystone = keystone_client.Client(auth_url=os.environ.get("OS_AUTH_URL"),
                                    username=os.environ.get("OS_USERNAME"),
                                    password=os.environ.get("OS_PASSWORD"),
                                    tenant_name=os.environ.get("OS_TENANT_NAME"))

  num_vms = 0
  num_flavors = 0

  for tenant in keystone.tenants.list():
    if not tenant.name == "service":
      nova = nova_client.Client(username=os.environ.get("OS_USERNAME"),
                                api_key=os.environ.get("OS_PASSWORD"),
                                auth_url=os.environ.get("OS_AUTH_URL"),
                                project_id=tenant.name)

      num_vms += len(nova.servers.list())
      num_flavors = len(nova.flavors.list())

  print "Found " + str(num_vms) + " instances"

  if num_flavors > 0:
     sys.exit(STATE_OK)
  else:
     sys.exit(STATE_UNKNOWN)
except Exception, e:
  print str(e)
  sys.exit(STATE_CRITICAL)
