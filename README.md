# CircuitCraft KiCad library packs

The official [KiCad libraries](https://gitlab.com/kicad/libraries) (schematic symbols, PCB
footprints and 3D models), packaged for [CircuitCraft](#what-circuitcraft-is): the symbols
and footprints converted to CircuitCraft's library format, the 3D models unchanged.

A pack is meant to be installed as CircuitCraft's base library. Every part keeps the library
and the name it has in KiCad, so that a design imported from KiCad can be matched to it.

This repository holds the recipe and the record of each pack. The packs themselves are the
files attached to the [releases](../../releases).

## Packs

| Pack | KiCad libraries | Built | Libraries | Components | Footprints | 3D models | Download |
|---|---|---|---|---|---|---|---|
| [`kicad-10.0.8-r1`](../../releases/tag/kicad-10.0.8-r1) | 10.0.8 | 2026-11-13 | 356 | 22,911 | 15,468 | 7,256 | libraries 19.7 MB, 3D models 645 MB (3.4 GB unpacked) |

A pack is named `kicad-<KiCad library release>-r<revision>`. The revision goes up when the
same KiCad release is converted again (a converter fix, a packaging change). Each pack's
`pack.json` in [`packs/`](packs) records the exact source commits and the converter that
made it.

## What is in a pack

| File | Contents |
|---|---|
| `circuitcraft-<pack>-libraries.zip` | `libraries/<KiCad library>.cclib`: one CircuitCraft library per KiCad symbol or footprint library, with the same names (`Device.cclib` holds `R`; footprints are keyed `Resistor_SMD:R_0603_1608Metric`). `libraries/index.json`: every component and footprint with its description, for searching without opening the libraries. `libraries/report.json`: what the conversion skipped or approximated. `LICENSE.md`: KiCad's licence. `ATTRIBUTION.md`: source, commits, licence and changes. |
| `circuitcraft-<pack>-3dmodels.zip` | `3dmodels/<Library>.3dshapes/<model>.step`: KiCad's STEP models, byte for byte, in KiCad's folder layout, with the `CREDITS.md` and disclaimer files that come with them. `LICENSE.md`: KiCad's licence. `ATTRIBUTION.md`: source, commit, licence. |
| `pack.json` | The pack's name, the KiCad release, source repositories and commits, the converter, counts, and the size and SHA-256 of each archive. |
| `SHA256SUMS.txt`, `SHA256SUMS.txt.sig` | Checksums of the three files above, and their signature. |

Footprints name their model as `${KICAD10_3DMODEL_DIR}/<Library>.3dshapes/<model>.step`, as
KiCad does; point that path variable at the unpacked `3dmodels` folder.

## Licence and attribution

The KiCad libraries are © their contributors and are licensed under the
[Creative Commons CC-BY-SA 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/legalcode)
with an exception for designs that use them. The full text, as distributed with the
libraries, is in [`KICAD-LICENSE.md`](KICAD-LICENSE.md) and in every archive; see also
<https://www.kicad.org/libraries/license/>.

- **The packs are adapted material and are distributed under that same licence** (CC-BY-SA 4.0
  with the KiCad libraries exception). If you redistribute a pack or part of it, keep the
  licence and the attribution documents with it.
- **Your designs are yours.** Under the exception, a design that uses these parts, and the
  files generated from it, do not have to be shared under this or any licence.
- **Source and credit:** KiCad Libraries, <https://gitlab.com/kicad/libraries>
  ([kicad-symbols](https://gitlab.com/kicad/libraries/kicad-symbols),
  [kicad-footprints](https://gitlab.com/kicad/libraries/kicad-footprints),
  [kicad-packages3D](https://gitlab.com/kicad/libraries/kicad-packages3D)), at the release tag
  each pack names. The authors of individual 3D models are credited in the `CREDITS.md` files
  kept beside the models.
- **What was changed:** symbols and footprints were converted to CircuitCraft's format
  (coordinates, pin and pad shapes, text, 3D model references). Some details are approximated
  or left out; each pack's `report.json` lists them. The 3D models, credits and disclaimers
  are not changed. Files that are not library content (build scripts, documentation of the
  3D viewer's materials) are left out.
- This project is not affiliated with or endorsed by the KiCad project. KiCad is a trademark
  of its owners.

The libraries are provided without warranty of any kind, as KiCad's licence says. Check a
footprint against the manufacturer's datasheet before you order boards.

The scripts in [`tools/`](tools) are this repository's own work, under the MIT licence or
the Apache License 2.0, at your choice.

## Known differences from KiCad's libraries

For `kicad-10.0.8-r1` (figures from [`packs/kicad-10.0.8-r1/report.json`](packs/kicad-10.0.8-r1/report.json)
and `tools/check_models.py`):

- Every symbol (22,911) and every footprint (15,468) was converted; none was skipped. 292
  footprints carry a conversion note: a custom pad with holes stored as one outline, glue-layer
  circles not imported, chamfered pads with rounded corners imported as chamfered only, and
  similar.
- 35 components name a footprint that KiCad's footprint libraries do not hold at this release.
  The names are kept as written.
- Of the 15,468 footprints, 7,519 have their 3D model in the pack, 7,337 name a model that
  KiCad's model library does not contain (for example every footprint of `Connector_Wire`,
  which has no models upstream), and 612 name none. The references are kept as KiCad wrote
  them, so a model added to a later KiCad release is found without converting again. The
  pack holds every model KiCad publishes: 7,256 files.
- KiCad's VRML models (`.wrl`) are not part of KiCad's model library at this release and not
  part of the pack; CircuitCraft reads STEP.
- Components carry KiCad's library name, footprint filters and keywords as parameters
  (`KiCadLibrary`, `FootprintFilters`, `Keywords`).

## Checking a download

```sh
sha256sum -c SHA256SUMS.txt
ssh-keygen -Y verify -f allowed_signers -I release@circuitcraft -n circuitcraft-release \
  -s SHA256SUMS.txt.sig < SHA256SUMS.txt
```

[`allowed_signers`](allowed_signers) in this repository holds the public key the packs are
signed with.

## How a pack is built

1. Clone the three KiCad library repositories at the release tag:
   `git clone --depth 1 --branch <tag> https://gitlab.com/kicad/libraries/kicad-symbols.git`
   (and `kicad-footprints`, `kicad-packages3D`).
2. Convert the symbols and footprints:
   `circuitcraft-cli kicad-lib convert --symbols kicad-symbols --footprints kicad-footprints --out converted`
3. Package: `python tools/build_pack.py --converted converted --symbols kicad-symbols
   --footprints kicad-footprints --models kicad-packages3D --kicad <tag> --revision <n>
   --converter "<circuitcraft-cli --version>" --date <YYYY-MM-DD> --out out`
   (`tools/check_models.py` compares the footprints' model references with the model library).
4. Sign `SHA256SUMS.txt` and attach the five files to a release named after the pack.

The archives are written with sorted entries and fixed timestamps. The conversion itself is
not byte-reproducible: `index.json` records when each library file was written.

## What CircuitCraft is

CircuitCraft is a PCB design application (schematic capture, libraries, PCB layout, rules,
fabrication outputs, 3D, simulation) written in Rust, in development. It is not public yet;
this repository exists so that its base library has a public, versioned, attributed source.
