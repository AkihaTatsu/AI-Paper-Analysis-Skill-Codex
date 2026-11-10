# Byte-Safe Report Editing

Write complete reports and report patches with `apply_patch`, raw UTF-8 bytes,
or another operation that preserves text literally. Never place Markdown or
TeX in an interpreted string that can turn `\t`, `\n`, `\r`, or another
backslash sequence into a control character.
