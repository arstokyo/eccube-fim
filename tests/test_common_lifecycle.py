from unittest.mock import patch

import common.lifecycle as cl


# ---------------------------------------------------------------------------
# stop_and_disable_units
# ---------------------------------------------------------------------------

def test_stop_and_disable_units_calls_systemctl():
    with patch("common.lifecycle.subprocess.run") as mock_run:
        cl.stop_and_disable_units(["foo.timer", "bar.timer"])
    assert mock_run.call_count == 4   # 2 units × (stop + disable)
    cmds = [c.args[0] for c in mock_run.call_args_list]
    assert ["systemctl", "stop",    "foo.timer"] in cmds
    assert ["systemctl", "disable", "foo.timer"] in cmds
    assert ["systemctl", "stop",    "bar.timer"] in cmds
    assert ["systemctl", "disable", "bar.timer"] in cmds


def test_stop_and_disable_units_empty_list():
    with patch("common.lifecycle.subprocess.run") as mock_run:
        cl.stop_and_disable_units([])
    mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# remove_unit_files
# ---------------------------------------------------------------------------

def test_remove_unit_files_unlinks_files_and_reloads(tmp_path):
    (tmp_path / "a.timer").write_text("")
    (tmp_path / "b.service").write_text("")
    with patch("common.lifecycle.subprocess.run") as mock_run:
        cl.remove_unit_files(["a.timer", "b.service"], str(tmp_path))
    assert not (tmp_path / "a.timer").exists()
    assert not (tmp_path / "b.service").exists()
    mock_run.assert_called_once_with(["systemctl", "daemon-reload"], check=False)


def test_remove_unit_files_missing_files_are_silently_skipped(tmp_path):
    with patch("common.lifecycle.subprocess.run"):
        cl.remove_unit_files(["nonexistent.timer"], str(tmp_path))   # no exception


# ---------------------------------------------------------------------------
# remove_lib_subdir
# ---------------------------------------------------------------------------

def test_remove_lib_subdir_removes_only_target(tmp_path):
    (tmp_path / "fim").mkdir()
    (tmp_path / "fim" / "cli.py").write_text("")
    (tmp_path / "common").mkdir()
    cl.remove_lib_subdir(str(tmp_path), "fim")
    assert not (tmp_path / "fim").exists()
    assert (tmp_path / "common").exists()


def test_remove_lib_subdir_missing_subdir_is_noop(tmp_path):
    cl.remove_lib_subdir(str(tmp_path), "nonexistent")   # no exception


# ---------------------------------------------------------------------------
# remove_common_if_no_companion
# ---------------------------------------------------------------------------

def test_remove_common_removes_when_no_marker(tmp_path):
    common_dir = tmp_path / "lib" / "common"
    common_dir.mkdir(parents=True)
    marker = tmp_path / "marker"   # does NOT exist
    cl.remove_common_if_no_companion(str(tmp_path / "lib"), str(marker))
    assert not common_dir.exists()
    assert not (tmp_path / "lib").exists()   # rmdir'd because empty


def test_remove_common_retains_when_marker_present(tmp_path, capsys):
    common_dir = tmp_path / "lib" / "common"
    common_dir.mkdir(parents=True)
    marker = tmp_path / "marker"
    marker.write_text("")   # companion is installed
    cl.remove_common_if_no_companion(str(tmp_path / "lib"), str(marker))
    assert common_dir.exists()
    assert "retained" in capsys.readouterr().out


def test_remove_common_leaves_lib_dir_when_not_empty(tmp_path):
    lib = tmp_path / "lib"
    (lib / "common").mkdir(parents=True)
    (lib / "malware").mkdir()   # sibling still present — lib not empty after common/ removed
    marker = tmp_path / "marker"   # no marker — common should be removed
    cl.remove_common_if_no_companion(str(lib), str(marker))
    assert not (lib / "common").exists()
    assert (lib / "malware").exists()
    assert lib.exists()   # lib itself kept because malware/ is still there


# ---------------------------------------------------------------------------
# fim_installed
# ---------------------------------------------------------------------------

def test_fim_installed_true_when_fim_lib_present(tmp_path):
    lib = tmp_path / "lib"
    (lib / "fim").mkdir(parents=True)
    assert cl.fim_installed(str(lib), str(tmp_path / "no-fim-bin")) is True


def test_fim_installed_true_when_fim_bin_present(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    fim_bin = tmp_path / "eccube-fim"
    fim_bin.write_text("")
    assert cl.fim_installed(str(lib), str(fim_bin)) is True


def test_fim_installed_false_when_both_absent(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    assert cl.fim_installed(str(lib), str(tmp_path / "no-fim-bin")) is False


# ---------------------------------------------------------------------------
# remove_common_if_fim_absent
# ---------------------------------------------------------------------------

def test_remove_common_if_fim_absent_retains_when_fim_lib_present(tmp_path, capsys):
    lib = tmp_path / "lib"
    (lib / "fim").mkdir(parents=True)
    (lib / "common").mkdir()
    cl.remove_common_if_fim_absent(str(lib), str(tmp_path / "no-fim-bin"))
    assert (lib / "common").exists()
    assert "retained" in capsys.readouterr().out


def test_remove_common_if_fim_absent_retains_when_fim_bin_present(tmp_path, capsys):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "common").mkdir()
    fim_bin = tmp_path / "eccube-fim"
    fim_bin.write_text("")
    cl.remove_common_if_fim_absent(str(lib), str(fim_bin))
    assert (lib / "common").exists()
    assert "retained" in capsys.readouterr().out


def test_remove_common_if_fim_absent_cleans_when_fim_absent(tmp_path, capsys):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "common").mkdir()
    cl.remove_common_if_fim_absent(str(lib), str(tmp_path / "no-fim-bin"))
    assert not (lib / "common").exists()
    assert not lib.exists()    # empty lib dir removed
    assert "removed" in capsys.readouterr().out
