"""Prepare the embedded payload from the official Windows x64 runtimes."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python_zip", type=Path)
    parser.add_argument("webview2", type=Path, help="Extracted Fixed Version runtime directory")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]

    if not (args.webview2 / "msedgewebview2.exe").is_file():
        parser.error("The WebView2 directory must contain msedgewebview2.exe.")

    app_files = (
        "desktop_backend.py", "browser_import.py", "core.py", "extra_sources.py", "catalog_sources.py", "search_filters.py",
        "interface/index.html", "interface/style.css", "interface/desk.js", "interface/i18n.js", "interface/brand-banner.png",
        "interface/backdrop.png",
        "browser/TorrentFindr.Browser.exe",
        "browser/WebView2-LICENSE.txt", "browser/WebView2-NOTICE.txt",
        "browser/dotnet-LICENSE.txt", "browser/dotnet-NOTICES.txt", "browser/dotnet-desktop-LICENSE.txt",
    )
    with ZipFile(args.python_zip) as python:
        names = python.namelist()
        path_files = [name for name in names if name.endswith("._pth")]
        if "python.exe" not in names or len(path_files) != 1:
            parser.error("Use the official Python Windows x64 embeddable ZIP.")
        path_file = path_files[0]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(args.output, "w", compression=ZIP_DEFLATED, compresslevel=3) as bundle:
            for name in names:
                data = python.read(name)
                if name == path_file:
                    # The engine is isolated and imports the app modules from its parent directory.
                    data += b"\n..\n"
                bundle.writestr(f"engine/{name}", data)
            for name in app_files:
                compression = ZIP_STORED if name.endswith(".exe") else ZIP_DEFLATED
                bundle.write(project / name, name, compress_type=compression)
            for file in sorted(args.webview2.rglob("*")):
                if file.is_file():
                    relative = file.relative_to(args.webview2).as_posix()
                    bundle.write(file, f"webview2-runtime/{relative}")


if __name__ == "__main__":
    main()
