# Simple concat merge – assumes compatible structure
import sys, glob, os

out_path = "data/merged.xml.gz"  # adjust per country in workflow
files = glob.glob("data/**/*.xml", recursive=True)

if not files:
    print("No XML files found")
    sys.exit(1)

with open("data/merged.xml", "wb") as out:
    for f in files:
        with open(f, "rb") as inp:
            out.write(inp.read())

# gzip
import gzip, shutil
with open("data/merged.xml", "rb") as f_in:
    with gzip.open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

os.remove("data/merged.xml")
print(f"Merged & gzipped: {out_path}")
