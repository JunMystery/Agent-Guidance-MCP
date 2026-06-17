---
name: homelab-network-setup
description: Practical home and homelab network planning and readiness audits, covering gateways, switches, access points, IP plans, VLAN segmentation, local DNS filtering (Pi-hole), WireGuard VPN access, and change validation checklists.
origin: community
---

# Homelab Network Setup and Readiness

Use this skill to design a home or small-lab network that can grow without needing a full rebuild, and to audit readiness before modifying router, VLAN, DNS, firewall, or VPN configuration.

## When to Use

- Planning a new home network or redesigning an ISP-router-only setup.
- Splitting a flat network into trusted, IoT, guest, server, or management VLANs.
- Moving DHCP clients to Pi-hole, AdGuard Home, Unbound, or another local DNS resolver.
- Adding WireGuard, Tailscale, ZeroTier, or router-native VPN access.
- Reviewing whether a network change can lock the operator out of the gateway.

## Safety Rules

- **Keep the first step read-only**: Audit inventory, risks, staged plan, validation, and rollback before issuing commands.
- **Never expose administration UIs directly to the public internet** (gateway admin, DNS resolvers, SSH, NAS consoles, VPN management).
- **Require out-of-band console access** before changing management VLANs, trunk ports, firewall default policies, or DHCP settings.
- **Keep a working path back to the internet** before pointing the network at a new DNS resolver or VPN route.

## Device Roles & Gateway Options

```text
Internet
  |
Modem or ONT
  |
Gateway or router      NAT, firewall, DHCP, DNS, inter-VLAN routing
  |
Managed switch         wired clients, AP uplinks, optional VLAN trunks
  |
Access points          Wi-Fi only; ideally wired backhaul
Servers and NAS        stable addresses, DNS names, monitoring
Clients and IoT        DHCP pools, isolated later if VLANs are available
```

| Gateway Option | Best fit | Notes |
| --- | --- | --- |
| ISP router | Basic internet only | Limited control and often poor VLAN support |
| UniFi gateway | Managed home network | Good UI, ecosystem lock-in |
| OPNsense or pfSense | Flexible homelab | Strong VLAN, firewall, VPN, and DNS control |
| MikroTik | Advanced network users | Powerful, but easy to misconfigure |
| Linux router | Tinkerers | Document rollback before using as primary gateway |

## IP Addressing & DNS Naming Plan

Avoid the most common default, `192.168.1.0/24`, when you expect to use VPNs. It often conflicts with hotels, offices, and ISP routers.

```text
Example small homelab plan:

192.168.10.0/24  trusted clients
192.168.20.0/24  IoT and media devices
192.168.30.0/24  servers and NAS
192.168.40.0/24  guest Wi-Fi
192.168.99.0/24  network management

Gateway convention: .1
Infrastructure reservations: .2 through .49
Dynamic DHCP pool: .50 through .240
```

Use `home.arpa` for local names. It is reserved for home networks and avoids conflicts from names like `home.lan` (e.g. `nas.home.arpa`, `pihole.home.arpa`).

## VLAN And Trust-Zone Setup

Define the trust zones and map them:
- **Trusted**: Laptops, phones, admin workstations. Can reach shared services and management.
- **Servers**: NAS, Home Assistant, DNS resolver. Accepts narrow inbound flows from trusted clients.
- **IoT**: TVs, smart plugs, cameras. Internet access plus explicit exceptions only.
- **Guest**: Visitor devices. Internet-only, no LAN reachability.
- **Management**: Gateway, switches, APs. Reachable only from trusted admin devices.

Before implementing VLAN changes, verify that the gateway supports inter-VLAN routing/firewalls, the switches support VLAN tagging, and the APs can map SSIDs to VLANs.

## DNS Filtering & VPN Readiness

- **Pi-hole / DNS filters**: Give the resolver a reserved address before utilizing it in DHCP options. Point DHCP DNS options at it. Keep the gateway or a second resolver available as a temporary fallback.
- **WireGuard / VPNs**: Decide what the VPN is allowed to reach before generating keys or opening ports (e.g. split tunnel to one subnet vs full tunnel). Verify dynamic DNS or CGNAT status before setting up port forwards.

## Change Sequence (Staged Migration)

1. **Snapshot** the current topology, IP plan, DHCP leases, DNS settings, and firewall rules.
2. **Reserve infrastructure addresses** for gateway, DNS, controller, APs, and NAS.
3. **Create the new zone or VLAN** without moving critical devices.
4. **Move one test client** and validate DHCP, DNS, routing, internet, and block behavior.
5. **Add narrow firewall exceptions** for required flows.
6. **Move one low-risk device group**.
7. **Add VPN access** with the narrowest route.
8. **Document final state** and rollback instructions.

## Verification Checklist

- [ ] No management interface is reachable from guest, IoT, or the public internet
- [ ] DNS failure does not take down local console recovery access
- [ ] DHCP scope changes were tested on one client before broad rollout
- [ ] Firewall rules are default-deny between zones, with named exceptions
- [ ] Rollback steps are documented for the chosen platform

## See Also

- Skill: `network-interface-health`
- Skill: `network-config-validation`
