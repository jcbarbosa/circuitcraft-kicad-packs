"""Compare the 3D model references of the converted footprints with the model library."""
import glob, json, os, re, sys
conv, models = sys.argv[1], sys.argv[2]
refs = set(); nomodel = 0; total = 0; names = set(); odd = []
for f in glob.glob(os.path.join(conv, "*.cclib")):
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    for n, fp in d.get("footprints", {}).items():
        total += 1
        m = fp.get("model")
        if not m or not m.get("path"):
            nomodel += 1
            continue
        mm = re.match(r"\$\{([A-Z0-9_]+)\}/(.*)", m["path"])
        if mm:
            names.add(mm.group(1)); refs.add(mm.group(2))
        else:
            odd.append(m["path"])
have = set()
for d, dirs, fs in os.walk(models):
    dirs[:] = [x for x in dirs if x != ".git"]
    for x in fs:
        if x.lower().endswith((".step", ".stp")):
            have.add(os.path.relpath(os.path.join(d, x), models).replace(os.sep, "/"))
low = {h.lower() for h in have}
miss = sorted(r for r in refs if r.lower() not in low)
unused = len(have) - len({r.lower() for r in refs} & low)
print("footprints", total, "| without a model", nomodel, "| distinct model references", len(refs),
      "| path variables", sorted(names), "| other paths", len(odd), odd[:3])
print("model files", len(have), "| referenced and missing from the library", len(miss), miss[:6],
      "| model files no footprint names", unused)
