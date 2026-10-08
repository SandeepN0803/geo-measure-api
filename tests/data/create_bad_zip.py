import zipfile

with zipfile.ZipFile("tests/data/bad.zip", "w") as zf:
    zf.writestr("readme.txt", "This archive contains no Shapefile (.shp).")

print("Created bad.zip successfully")
