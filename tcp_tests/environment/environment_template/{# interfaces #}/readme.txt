Patterns from this folder are used for two purposes:
1. Configure the real node interfaces as specified in the inventory.
2. Provide the following list of interfaces for the underlay level:
  - br_mgm: Access from infrastructure management network / admin network / DHCP / PXE
  - br_ctl: OpenStack control network for internal services
  - br-prv: For tenant networks with VLAN segmentation
  - br-ten: For tenant networks with VXLAN segmentation
  - br-mesh: Endpoint for VXLAN tunnels that are used by br-ten
  - br-floating: Connection to the floating network
  - vhost0: for OpenContrail workloads