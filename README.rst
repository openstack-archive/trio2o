=========
Trio2o
=========

The Trio2o provides an OpenStack API gateway to allow multiple OpenStack
instances, spanning in one site or multiple sites or in hybrid cloud, to
be managed as a single OpenStack cloud.

The Trio2o and these managed OpenStack instances will use shared KeyStone
(with centralized or distributed deployment) or federated KeyStones for
identity management.

The Trio2o presents one big region to the end user in KeyStone. And each
OpenStack instance called a pod is a sub-region of the Trio2o in
KeyStone, and usually not visible to end user directly.

The Trio2o acts as OpenStack API gateway, can handle OpenStack API calls,
schedule one proper OpenStack instance if needed during the API calls handling,
forward the API calls to the appropriate OpenStack instance.

The end user can see availability zone(AZ) and use AZ to provision
VM, Volume, through the Trio2o. One AZ can include many OpenStack instances,
the Trio2o can schedule and bind OpenStack instance for the tenant inside one
AZ. A tenant's resources could be bound to multiple specific bottom OpenStack
instances in one or multiple AZs automatically.

* Free software: Apache license
* Design documentation: `Trio2o Design Blueprint <https://docs.google.com/document/d/1cmIUsClw964hJxuwj3ild87rcHL8JLC-c7T-DUQzd4k/>`_
* Wiki: https://wiki.openstack.org/wiki/trio2o
* Installation with DevStack: https://github.com/openstack/trio2o/blob/master/doc/source/
* Trio2o Admin API documentation: https://github.com/openstack/trio2o/blob/master/doc/source/api_v1.rst
* Source: https://github.com/openstack/trio2o
* Bugs: http://bugs.launchpad.net/trio2o
* Blueprints: https://launchpad.net/trio2o
