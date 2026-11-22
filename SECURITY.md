# Security

## Supported versions

The 1.x line receives fixes.

## Design

- The tool runs locally. It does not start a server, listen on a port or accept remote requests.
- It does not store credentials, tokens or passwords.
- Personal data stays in `data/`, which is ignored by git and is not included in the package.

## Network

Requests are read-only GET requests to:

- `dekudeals.com`
- `twoaveragegamers.com`
- `store.steampowered.com`
- `steamcommunity.com`
- `metacritic.com`

There is a request budget and a per-host rate limit. `--offline` skips all requests.

## Excel safety

- Text that starts with `=` is stored as text, so a game folder or wishlist title cannot become a formula.
- Control characters Excel rejects are removed from cells and comments.

## Reporting

Open a GitHub issue at https://github.com/IkerAbad/game-inventory/issues. Do not attach personal `data/` files. If the report contains sensitive details, use the repository's private security advisory instead.
