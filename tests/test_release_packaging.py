"""
Assertions about release packaging contracts:
  - release.yml publishes the expected runtime tarballs
  - generated installers include the required install functions and guards
"""
from pathlib import Path

_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# release.yml — workflow contract
# ---------------------------------------------------------------------------

def test_release_workflow_stamps_common_version():
    text = (_ROOT / ".github/workflows/release.yml").read_text()
    assert "common/version.py" in text
    assert "fim/version.py" not in text


def test_release_workflow_publishes_three_runtime_tarballs():
    text = (_ROOT / ".github/workflows/release.yml").read_text()
    assert "eccube-common-${{ github.ref_name }}.tar.gz" in text
    assert "eccube-fim-${{ github.ref_name }}.tar.gz" in text
    assert "eccube-malware-${{ github.ref_name }}.tar.gz" in text


def test_tool_tarballs_do_not_bundle_common():
    text = (_ROOT / ".github/workflows/release.yml").read_text()
    fim_block = text.split("Build FIM tarball", 1)[1].split("Build malware tarball", 1)[0]
    malware_block = text.split("Build malware tarball", 1)[1].split("Build plugin tarball", 1)[0]
    assert "cp -r common" not in fim_block
    assert "cp -r common" not in malware_block
    assert "bin/eccube-fim" in fim_block
    assert "bin/eccube-malware" in malware_block


def test_malware_tarball_includes_systemd_templates():
    text = (_ROOT / ".github/workflows/release.yml").read_text()
    malware_block = text.split("Build malware tarball", 1)[1].split("Build plugin tarball", 1)[0]
    assert "systemd/clamav-*" in malware_block


# ---------------------------------------------------------------------------
# generated installers
# ---------------------------------------------------------------------------

def test_generated_installers_install_common():
    assert "install_common_library" in (_ROOT / "install.sh").read_text()
    assert "install_common_library" in (_ROOT / "install-malware.sh").read_text()


def test_generated_installers_guard_companion_version():
    assert "guard_existing_malware_version" in (_ROOT / "install.sh").read_text()
    assert "guard_existing_fim_version" in (_ROOT / "install-malware.sh").read_text()


def test_generated_fim_installer_order():
    """install_common_library must be called before install_fim_library at every call site."""
    lines = (_ROOT / "install.sh").read_text().splitlines()
    call_common = [i for i, ln in enumerate(lines) if ln.strip() == "install_common_library"]
    call_fim    = [i for i, ln in enumerate(lines) if ln.strip() == "install_fim_library"]
    assert call_common and call_fim, "both call sites must exist"
    # each common call must precede the nearest fim call at that site
    for common_lineno, fim_lineno in zip(call_common, call_fim):
        assert common_lineno < fim_lineno


def test_generated_malware_installer_installs_common_before_malware():
    """install_common_library must be called before install_malware_library at the call site."""
    lines = (_ROOT / "install-malware.sh").read_text().splitlines()
    call_common  = [i for i, ln in enumerate(lines) if ln.strip() == "install_common_library"]
    call_malware = [i for i, ln in enumerate(lines) if ln.strip() == "install_malware_library"]
    assert call_common and call_malware, "both call sites must exist"
    assert call_common[0] < call_malware[0]


def test_generated_malware_installer_renders_systemd_templates():
    text = (_ROOT / "install-malware.sh").read_text()
    assert "_install_malware_unit" in text
    assert "clamav-scan.service" in text


def test_malware_installer_writes_version_stamp():
    text = (_ROOT / "install-malware.sh").read_text()
    assert "install_version_stamp" in text
