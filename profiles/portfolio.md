# Personal portfolio architecture preference

Optional guidance for Michaela's local development agents. This is not an
organisation standard, downstream project requirement, or mandatory CI policy.
Do not copy it into generated project instructions, modules, or consumer repos.

- For portfolio work, favour designs that demonstrate production platform
  thinking: explicit trust boundaries, managed identities, least privilege,
  network isolation, observability, recovery, and maintainable infrastructure.
- Explain concrete trade-offs and costs. Reuse suitable existing resources and
  modules; production thinking does not mean adding services without a need.
- Consider VNet integration for Azure workloads, with public ingress only where
  the integration requires it. For example, a GitHub webhook can need a public
  HTTPS endpoint while its Function accesses dependencies privately.
- This preference never authorises a network topology or deployment. The shared
  standards still reserve those decisions and per-command approvals for the user.
