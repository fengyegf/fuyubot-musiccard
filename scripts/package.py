#!/usr/bin/env python3
"""Build a FuyuBot plugin bundle for one target platform."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path
from zipfile import ZipInfo

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ID = "musiccard"
TARGETS = {
    "windows-x86_64": ("musiccard.dll", None),
    "linux-x86_64": ("libmusiccard.so", None),
    "macos-aarch64": ("libmusiccard.dylib", None),
    "android-aarch64": ("libmusiccard.so", "aarch64-linux-android"),
    "android-x86_64": ("libmusiccard.so", "x86_64-linux-android"),
}
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def normalize_version(value: str) -> str:
    version = value.removeprefix("v")
    if not SEMVER_RE.fullmatch(version):
        raise SystemExit(f"版本号必须是 semver，例如 1.2.0：{value!r}")
    return version


def add_file(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package a Rust build as a FuyuBot plugin bundle"
    )
    parser.add_argument("--platform", required=True, choices=sorted(TARGETS))
    parser.add_argument("--version", required=True, help="Semver or v-prefixed tag")
    parser.add_argument(
        "--target-dir",
        default="target",
        help="Cargo target root; platform triples are appended automatically",
    )
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()

    version = normalize_version(args.version)
    library_name, triple = TARGETS[args.platform]
    target_root = ROOT / args.target_dir
    release_dir = target_root / triple / "release" if triple else target_root / "release"
    library = release_dir / library_name
    if not library.is_file():
        raise SystemExit(f"找不到 {library}；请先执行 cargo build --release")

    output_dir = ROOT / args.output_dir
    bundle_dir = output_dir / f"bundle-{args.platform}"
    output_dir.mkdir(parents=True, exist_ok=True)
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)

    bin_dir = bundle_dir / "bin"
    bin_dir.mkdir(parents=True)
    shutil.copy2(library, bin_dir / library_name)

    manifest_path = ROOT / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("id") != PLUGIN_ID:
        raise SystemExit("plugin.json 的 schema/id 不正确")
    if manifest.get("kind") != "native" or manifest.get("abi") != 5:
        raise SystemExit("plugin.json 必须声明 native kind 和 ABI 5")

    entry = f"bin/{library_name}"
    manifest["version"] = version
    manifest["entry"] = entry
    manifest["platforms"] = [args.platform]
    (bundle_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    archive_path = output_dir / f"{PLUGIN_ID}-{version}-{args.platform}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        add_file(archive, bundle_dir / "plugin.json", "plugin.json")
        add_file(archive, bin_dir / library_name, entry)

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        expected_names = {"plugin.json", entry}
        if names != expected_names:
            raise SystemExit(
                f"生成的 ZIP 内容不正确，期望 {sorted(expected_names)}，"
                f"实际 {sorted(names)}"
            )
        packaged_manifest = json.loads(archive.read("plugin.json"))
        if packaged_manifest.get("version") != version:
            raise SystemExit("生成的 ZIP 中 version 与命令行版本不一致")
        if packaged_manifest.get("platforms") != [args.platform]:
            raise SystemExit("生成的 ZIP 中 platforms 与目标平台不一致")
        if packaged_manifest.get("entry") != entry:
            raise SystemExit("生成的 ZIP 中 entry 与目标文件不一致")

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"[OK] {archive_path} ({size_mb:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
