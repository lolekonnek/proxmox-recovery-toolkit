# Contributing to Proxmox Recovery Toolkit

Thank you for your interest in contributing to Proxmox Recovery Toolkit!

Contributions of all kinds are welcome, including bug reports, feature requests, code improvements, testing and documentation.

## Getting Started

1. Fork this repository.
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/proxmox-recovery-toolkit.git
   cd proxmox-recovery-toolkit
   ```

3. Create a new branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

The recommended development environment is Debian 12 (Bookworm).

Install the required dependencies:

```bash
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso python3
```

The project uses Debian Live and `live-build` to generate a bootable ISO image.

## Project Structure

```text
.
├── auto/                   # Debian Live configuration
├── config/                 # Live-build configuration
├── src/
│   └── proxmox_recovery/   # Application source code
├── tests/                  # Unit tests
├── build.sh                # ISO build script
└── README.md
```

## Coding Guidelines

When contributing code:

- Follow the existing project structure.
- Write readable and maintainable Python code.
- Use descriptive variable and function names.
- Handle errors explicitly.
- Avoid unnecessary dependencies.
- Keep functions focused on a single responsibility.
- Document non-obvious operations.
- Never commit passwords, API keys or other sensitive information.

## Safety Requirements

This project deals with storage devices and system recovery. Safety is a priority.

All contributions must follow these principles:

- Diagnostic operations should remain read-only.
- Never modify disks during automatic detection or scanning.
- Any operation that writes to a recovered system must be clearly documented.
- Destructive operations must require explicit user confirmation.
- Never silently format, initialize or repair storage devices.
- Recovery operations must only be used on systems the user is authorized to administer.
- Do not introduce operations that could cause unintended data loss.

Changes affecting disk operations, LVM, ZFS or filesystem mounting require particular care.

## Testing

Before submitting changes, run the unit tests:

```bash
python3 -m unittest discover -s tests -v
```

If your changes affect the ISO configuration, also test the build using Debian 12 (Bookworm).

Do not test potentially destructive recovery operations on production systems or disks containing important data.

## Reporting Bugs

When opening an issue, include:

- A clear description of the problem.
- Steps to reproduce the issue.
- Expected and actual behavior.
- Relevant logs or error messages.
- Your Debian version and hardware configuration, when relevant.

Never include passwords, private keys or sensitive system information in bug reports.

## Pull Requests

Before submitting a Pull Request:

1. Make sure your changes are focused and relevant.
2. Run the existing unit tests.
3. Verify that diagnostic operations remain read-only.
4. Update documentation if necessary.
5. Provide a clear description of your changes.
6. Reference related issues if applicable.

Keep Pull Requests reasonably small and easy to review.

## Commit Messages

Use descriptive commit messages.

Recommended prefixes:

- `feat:` – new functionality
- `fix:` – bug fixes
- `docs:` – documentation changes
- `test:` – test improvements
- `refactor:` – code restructuring
- `build:` – build system changes

Examples:

```text
feat: add disk detection support
fix: handle missing ZFS utilities
docs: improve recovery instructions
test: add LVM detection tests
build: update Debian Live configuration
```

## Code of Conduct

Be respectful and constructive when communicating with other contributors.

Harassment, discrimination and disrespectful behavior are not welcome.

## License

By contributing to this project, you agree that your contributions will be distributed under the project's existing license.

Thank you for helping improve Proxmox Recovery Toolkit!
