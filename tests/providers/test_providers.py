from rlc.cloud_repos.providers import configure_default, configure_provider


def test_dnf_vars_creation_and_backup(monkeypatch, mirrors_file, tmp_path):
    var_dir = tmp_path / "dnf_vars"
    var_dir.mkdir()
    (var_dir / "baseurl1").write_text("original-value")

    # Use setattr to patch the default path constant directly
    configure_default(var_dir, "https://foo1", "https://foo2")

    for var in ["baseurl1", "baseurl2"]:
        assert (var_dir / var).exists()

    assert (var_dir / "baseurl1.bak").exists()


def test_aws_clears_dnf_vars(tmp_path):
    var_dir = tmp_path / "dnf_vars"
    var_dir.mkdir()
    (var_dir / "baseurl1").write_text("original-value")
    (var_dir / "baseurl2").write_text("original-value")
    (var_dir / "product").write_text("rlc-9")
    (var_dir / "cloudcontentdir").write_text("/files")

    configure_provider(var_dir, "aws", "https://foo1", "https://foo2")

    for var in ["baseurl1", "baseurl2", "product", "cloudcontentdir"]:
        assert (var_dir / var).exists()

    assert (var_dir / "baseurl1").read_text().strip() == "https://foo1"
    assert (var_dir / "baseurl2").read_text().strip() == "https://foo2"

    for var in ["product", "cloudcontentdir"]:
        assert (var_dir / var).read_text().strip() == ""
