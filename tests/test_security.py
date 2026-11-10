import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from circumstances.errors import PackError
from circumstances.fetch import ResolverPolicy, _extract_tar, _extract_zip, confined_path


def test_confined_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(PackError, match="escapes"):
        confined_path(tmp_path, "../../secret")


def test_zip_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../../secret", "value")
    with pytest.raises(PackError, match="escapes"):
        _extract_zip(archive, tmp_path / "out", ResolverPolicy())


def test_tar_rejects_symbolic_link(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as handle:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        handle.addfile(info, io.BytesIO())
    with pytest.raises(PackError, match="special file"):
        _extract_tar(archive, tmp_path / "out", ResolverPolicy())


def test_archive_file_limit(tmp_path: Path) -> None:
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("one", "1")
        handle.writestr("two", "2")
    policy = ResolverPolicy(max_files=1)
    with pytest.raises(PackError, match="too many"):
        _extract_zip(archive, tmp_path / "out", policy)

