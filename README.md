# RLC Cloud Repos - Cloud-Agnostic Repository Auto-Configuration

## Overview

**RLC Cloud Repos** is a **cloud-init-powered, cloud-agnostic** repository configuration utility designed to:

- Automatically **configure DNF/YUM repositories** for Rocky Linux by CIQ (RLC) instances in the Cloud.
- **Dynamically select the best repository mirror** based on cloud provider and region.
- **Integrate with Cloud-Init**, ensuring repo configuration happens early in the boot process.
- **Deploy updates via RPM packaging**, making it easy to manage at scale.

## Problem Statement

Deploying and Running Rocky Linux on multiple cloud providers (AWS, Azure, GCP, OCI) requires custom repository configuration:

- Mirrors vary per provider and region.
- Network performance and bandwidth metering demand regional proximity.
- Instance metadata varies widely.
- Fallbacks when a mirror is unavailable (e.g., AWS instances in `us-west-1` fallback to `us-east-1`).
- Ensuring Cloud-Init properly integrates the repository configurations during instance boot.

## Key Benefits

1. **Zero-Touch Configuration** – Just boot the VM and it configures itself.
2. **Performance-Aware** – Selects pre-configured available mirror.
3. **Cloud-Native** – Leverages `cloud-init query`, not hand-coded API logic.
4. **Dynamic and Safe** – Uses a marker file to prevent reconfig unless explicitly allowed or on package update.

---

## **Architecture**

The system is designed as **modular components** that work together to **detect cloud provider, determine region, configure repositories, and integrate with Cloud-Init**.

### **System Flow**

```ascii
+----------------------------+
|     Instance Boot          |
+----------------------------+
           |
           v
+--------------------------------+
| Detect Cloud Provider & Region |
| via cloud-init                 |
+--------------------------------+
           |
           v
+----------------------------+
| Select Primary + Backup    |
| Mirrors from region map    |
+----------------------------+
           |
           v
+----------------------------+
| Configure DNF Variables    |
| in /etc/dnf/vars/          |
+----------------------------+
           |
           v
+----------------------------+
| Touch marker file to skip  |
| reconfiguration next boot  |
+----------------------------+
```

---

## Core Components

### ☁️ `cloud_metadata.py`

- Uses `cloud-init query` to fetch:
  - Provider name
  - Region
- Exits early with an error if cloud-init query fails or is unavailable.

### 📦 `repo_config.py`

- Generates DNF Variables from cloud-init metadata.
- Supports:
  - Primary mirror
  - Backup mirror
  - Region
- Maps variables against `ciq-mirrors.yaml` matrix
- CasC (Configuration As Code) Versioned.
  - No code changes required for _any_ mirror changes.

### 🧠 `main.py`

- Entry point triggered by cloud-init or manual run.
- Checks for marker file to skip duplicate configuration.
- Writes a marker file once run to prevent recurrent reconfiguring at reboot.

---

## Installation & Usage

### 📦 Build Source Distribution

To generate the source tarball used for packaging:

```bash
make sdist
```

This will produce a `.tar.gz` source archive in the `dist/` directory, suitable for consumption by downstream RPM packaging workflows.

---

### 🚀 Manually Trigger Repository Configuration

```bash
rlc-cloud-repos
```

This will:

- Detect cloud metadata using `cloud-init query`
- Write marker file to skip reconfig on next boot

---

## Supported Cloud Providers

The following providers are supported natively via `cloud-init` metadata detection:

- **AWS**
- **Azure**
- **Google Cloud Platform (GCP)**
- **Oracle Cloud Infrastructure (OCI)**

Mirror mapping is handled via a region → mirror YAML file (`ciq-mirrors.yaml`) shipped in the package.

---

## Configuration

- Mirror selection logic is data-driven via `ciq-mirrors.yaml`
- Configuration persists indefinitely until removed/updated.

### Plugin System for Repository Providers

RLC Cloud Repos includes a plugin system designed for **repository owners and maintainers** who need to integrate non-standard or add-on DNF repositories with the cloud-aware repository configuration system.

This system allows repository providers to:

- Add custom DNF variables specific to their repository infrastructure
- Integrate with cloud-aware repository selection without modifying core RLC code
- Support repository-specific metadata or authentication requirements
- Extend repository configurations based on cloud provider/region combinations

#### Plugin Directory

Repository plugins are shell scripts placed in `/etc/rlc-cloud-repos/plugins.d/` and must:

- Have a `.sh` extension
- Be executable (`chmod +x`)
- Be owned by root
- Not be world-writable

#### Plugin Interface

Plugins receive cloud metadata as command-line arguments:

- `--provider` - Cloud provider name (aws, azure, gcp, etc.)
- `--region` - Cloud region
- `--primary-url` - Primary mirror URL selected by RLC
- `--backup-url` - Backup mirror URL selected by RLC

**Parameter Usage**: Plugins may use any or all of these parameters as needed. It's perfectly acceptable for a plugin to ignore parameters that aren't relevant to its functionality (e.g., a plugin that sets static variables regardless of provider or region).

**Output Format**: Repository plugins should output `key=value` pairs to stdout for any additional DNF variables needed by their repositories.

**Error Handling Contract**:

- **Exit Code 0**: Success - Plugin executed successfully, any stdout output will be processed
- **Exit Code > 0**: Error - Plugin failed, stdout output will be ignored
- **stderr Output**: Error messages and logging - Will be captured and logged by RLC for debugging

**Forward Compatibility Requirement**: Plugins must gracefully handle unknown command-line arguments without error. Future versions of RLC Cloud Repos may pass additional arguments, and plugins should ignore unrecognized options to maintain compatibility.

#### Repository Integration Templates

Two plugin templates are available after package installation to help repository maintainers integrate with RLC's cloud-aware configuration:

**Simple Template** - Basic functionality:

```
/usr/share/doc/rlc-cloud-repos/simple.sh.template
```

**Complete Template** - Comprehensive examples with advanced features:

```
/usr/share/doc/rlc-cloud-repos/complete.sh.template
```

Repository maintainers can choose the appropriate template based on their integration needs.

#### Example Repository Plugin Deployment

```bash
# Repository maintainers would typically distribute plugins via their RPM packages
# which would install to /etc/rlc-cloud-repos/plugins.d/
# Then set up a soft requirement (recommends) on python3-rlc-cloud-repos

# For development/testing - use simple template:
sudo cp /usr/share/doc/rlc-cloud-repos/simple.sh.template \
        /etc/rlc-cloud-repos/plugins.d/my-repo.sh

# Or use complete template for advanced features:
sudo cp /usr/share/doc/rlc-cloud-repos/complete.sh.template \
        /etc/rlc-cloud-repos/plugins.d/my-repo.sh

# Make executable and customize for repository needs
sudo chmod 755 /etc/rlc-cloud-repos/plugins.d/my-repo.sh
```

Plugins execute after core RLC repository configuration, allowing repository providers to layer additional DNF variables or repository-specific configurations on top of the base cloud-aware setup.

---

## Development Notes

- Touch file at `/etc/rlc-cloud-repos/.configured` used to block rerun
- Logs only to stdout/stderr
- The included RPM spec (rpm/python3-rlc-cloud-repos.spec) handles the marker file lifecycle:
  1. Creates the marker file on initial install (%post).
  2. Removes the marker file on upgrade (%posttrans) and uninstall (%postun) to allow reconfiguration.

---

## 🧠 Development Notes

### 🔀 Current Development Branch

Create branches off of `git@github.com:ctrliq/rlc-cloud-repos.git Branch: main`
to develop PRs.

### Testing

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install development dependencies:

```bash
make dev
```

Run tests:

```bash
make test
```

---

## **License**

**RLC Cloud Repos** is licensed under the **MIT License**.

---

## **Authors**

**CIQ Automation and Delivery Team**
[https://github.com/ctrliq/rlc-cloud-repos](https://github.com/ctrliq/rlc-cloud-repos)
