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

---

## **License**

**RLC Cloud Repos** is licensed under the **MIT License**.

---

## **Authors**

**CIQ Solutions Delivery Engineering Team**
[https://github.com/ctrliq/rlc-cloud-repos](https://github.com/ctrliq/rlc-cloud-repos)
