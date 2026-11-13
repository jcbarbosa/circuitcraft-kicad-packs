#!/usr/bin/env python3
"""Package a converted KiCad library as a CircuitCraft base-library pack.

Inputs (all local folders):
  --converted DIR   output of `circuitcraft-cli kicad-lib convert` (one .cclib per KiCad
                    library, index.json, report.json)
  --symbols DIR     checkout of gitlab.com/kicad/libraries/kicad-symbols at the release tag
  --footprints DIR  checkout of .../kicad-footprints at the same tag
  --models DIR      checkout of .../kicad-packages3D at the same tag
  --kicad VERSION   the KiCad library release (the tag), e.g. 10.0.8
  --revision N      revision of this pack for that KiCad release (1, 2, ...)
  --converter TEXT  what converted it, e.g. "circuitcraft-cli 1.18.0 (682f61a2e)"
  --out DIR         where the archives, pack.json and SHA256SUMS.txt are written

Output (names carry the pack id `kicad-<version>-r<revision>`):
  circuitcraft-<id>-libraries.zip   the converted libraries, index.json, report.json
  circuitcraft-<id>-3dmodels.zip    KiCad's STEP models, unchanged, in KiCad's folder layout
  pack.json                         what the pack is, where it came from, sizes and checksums
  SHA256SUMS.txt                    checksums of the three files above

Both archives carry KiCad's LICENSE.md and an ATTRIBUTION.md (where the content comes from,
at which commits, under which licence, and what was changed); the model archive keeps the
CREDITS.md and disclaimer files that are distributed with the models. Archives are written
with sorted entries and a fixed timestamp.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile

STAMP = (2020, 1, 1, 0, 0, 0)
LICENCE = "CC-BY-SA-4.0 with the KiCad libraries exception"
REPOS = {
    "symbols": "https://gitlab.com/kicad/libraries/kicad-symbols",
    "footprints": "https://gitlab.com/kicad/libraries/kicad-footprints",
    "models": "https://gitlab.com/kicad/libraries/kicad-packages3D",
}


def commit_of(folder):
    out = subprocess.run(["git", "-C", folder, "rev-parse", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_zip(path, entries):
    """entries: sorted list of (name in the archive, source file or bytes). Returns (count, bytes)."""
    total = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for name, src in entries:
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            if isinstance(src, bytes):
                total += len(src)
                z.writestr(info, src)
                continue
            total += os.path.getsize(src)
            with open(src, "rb") as f, z.open(info, "w", force_zip64=True) as out:
                for block in iter(lambda: f.read(1 << 20), b""):
                    out.write(block)
    return len(entries), total


def attribution(pack_id, kicad, sources, converter, what, changed):
    """The ATTRIBUTION.md of an archive: source, licence and changes, as CC-BY-SA asks."""
    lines = [
        "# Attribution",
        "",
        "%s of the CircuitCraft KiCad library pack `%s`." % (what, pack_id),
        "",
        "- **Source:** the KiCad libraries, https://gitlab.com/kicad/libraries, release %s:" % kicad,
    ]
    for k in sorted(sources):
        lines.append("  - %s at commit `%s`" % (sources[k]["repository"], sources[k]["commit"]))
    lines += [
        "- **Authors:** the KiCad Libraries contributors. Authors of individual 3D models are",
        "  credited in the `CREDITS.md` files beside the models.",
        "- **Licence:** Creative Commons CC-BY-SA 4.0 with the KiCad libraries exception; the text",
        "  distributed with the libraries is `LICENSE.md` in this archive",
        "  (https://creativecommons.org/licenses/by-sa/4.0/legalcode,",
        "  https://www.kicad.org/libraries/license/). This archive is distributed under the same",
        "  licence. Designs that use the parts are covered by the exception.",
        "- **Changes:** %s" % changed,
        "- **Packaged by:** https://github.com/jcbarbosa/circuitcraft-kicad-packs, not affiliated",
        "  with or endorsed by the KiCad project. No warranty of any kind.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def library_entries(converted, symbols):
    names = sorted(n for n in os.listdir(converted)
                   if n.endswith((".cclib", ".ccschlib", ".ccpcblib")) or n in ("index.json", "report.json"))
    entries = [("libraries/" + n, os.path.join(converted, n)) for n in names]
    entries.append(("LICENSE.md", os.path.join(symbols, "LICENSE.md")))
    return sorted(entries)


def model_entries(models):
    entries = []
    kept_notes = 0
    for root, dirs, files in os.walk(models):
        dirs[:] = sorted(d for d in dirs if d != ".git" and not d.startswith("."))
        rel_dir = os.path.relpath(root, models).replace("\\", "/")
        top = rel_dir.split("/")[0]
        in_library = top.endswith(".3dshapes")
        for f in sorted(files):
            low = f.lower()
            rel = f if rel_dir == "." else rel_dir + "/" + f
            if in_library and low.endswith((".step", ".stp")):
                entries.append(("3dmodels/" + rel, os.path.join(root, f)))
            elif low == "credits.md" or low.endswith("disclaimer.md") or (rel_dir == "." and low == "license.md"):
                # Attribution and licence documents distributed with the models.
                name = "LICENSE.md" if rel_dir == "." and low == "license.md" else "3dmodels/" + rel
                entries.append((name, os.path.join(root, f)))
                kept_notes += 1
    return sorted(entries), kept_notes


def counts(converted):
    out = {}
    index = os.path.join(converted, "index.json")
    if os.path.isfile(index):
        with open(index, encoding="utf-8") as f:
            libs = json.load(f).get("libraries", {})
        out["libraries"] = len(libs)
        out["components"] = sum(len(v.get("components", [])) for v in libs.values())
        out["footprints"] = sum(len(v.get("footprints", [])) for v in libs.values())
    return out


def main():
    ap = argparse.ArgumentParser()
    for a in ("converted", "symbols", "footprints", "models", "kicad", "revision", "converter", "out"):
        ap.add_argument("--" + a, required=True)
    ap.add_argument("--date", required=True, help="the build date, YYYY-MM-DD")
    o = ap.parse_args()
    pack_id = "kicad-%s-r%s" % (o.kicad, o.revision)
    os.makedirs(o.out, exist_ok=True)
    lib_zip = "circuitcraft-%s-libraries.zip" % pack_id
    mod_zip = "circuitcraft-%s-3dmodels.zip" % pack_id

    sources = {k: {"repository": REPOS[k], "tag": o.kicad, "commit": commit_of(getattr(o, k))}
               for k in ("symbols", "footprints", "models")}
    libs = library_entries(o.converted, o.symbols)
    libs.append(("ATTRIBUTION.md", attribution(
        pack_id, o.kicad, {k: sources[k] for k in ("symbols", "footprints")}, o.converter,
        "The symbol and footprint libraries",
        "converted to CircuitCraft's library format by %s (coordinates, pin and pad shapes, "
        "text, 3D model references); what was approximated or left out is listed in "
        "`libraries/report.json`." % o.converter)))
    n_libs, lib_bytes = write_zip(os.path.join(o.out, lib_zip), sorted(libs))
    models, notes = model_entries(o.models)
    models.append(("ATTRIBUTION.md", attribution(
        pack_id, o.kicad, {"models": sources["models"]}, o.converter,
        "The 3D models",
        "none to the models, credits and disclaimers (the files are KiCad's, byte for byte); "
        "files that are not library content were left out.")))
    n_models, model_bytes = write_zip(os.path.join(o.out, mod_zip), sorted(models))

    files = []
    for name, entries, unpacked in ((lib_zip, n_libs, lib_bytes), (mod_zip, n_models, model_bytes)):
        p = os.path.join(o.out, name)
        files.append({"name": name, "bytes": os.path.getsize(p), "sha256": sha256(p),
                      "entries": entries, "unpacked_bytes": unpacked})
    c = counts(o.converted)
    c["models"] = sum(1 for n, _ in models if n.lower().endswith((".step", ".stp")))
    c["attribution_documents"] = notes
    pack = {
        "pack": pack_id,
        "format": 1,
        "kicad_version": o.kicad,
        "revision": int(o.revision),
        "built": o.date,
        "converter": o.converter,
        "licence": LICENCE,
        "sources": sources,
        "contents": c,
        "files": files,
    }
    with open(os.path.join(o.out, "pack.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(pack, f, indent=2, sort_keys=False)
        f.write("\n")
    with open(os.path.join(o.out, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        for name in (lib_zip, mod_zip, "pack.json"):
            f.write("%s  %s\n" % (sha256(os.path.join(o.out, name)), name))
    json.dump(pack, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
