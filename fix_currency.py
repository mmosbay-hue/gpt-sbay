"""Đổi USD → VNĐ trong tất cả frontend files."""
import glob

REPLACE = [
    ("'$' + d.", "'' + d."),
    ("'$' + ", "'' + "),
    ("$0", "0₫"),
    ("$9.99", "99.000₫"),
    ("$29.99", "299.000₫"),
    ("$${p.price}", "${p.price.toLocaleString()}₫"),
    ("$${p.amount}", "${p.amount.toLocaleString()}₫"),
    ("$${c.amount}", "${c.amount.toLocaleString()}₫"),
    ("$${data.price}", "${data.price.toLocaleString()}₫"),
]

files = glob.glob("frontend/**/*.html", recursive=True) + glob.glob("frontend/**/*.js", recursive=True)
for f in files:
    try:
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        original = content
        for old, new in REPLACE:
            content = content.replace(old, new)
        if content != original:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"Updated: {f}")
    except Exception as e:
        print(f"Error {f}: {e}")

print("Done")
