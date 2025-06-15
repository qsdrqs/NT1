import argparse
from clang import cindex

ARRAY_KINDS = {
    cindex.TypeKind.CONSTANTARRAY,
    cindex.TypeKind.INCOMPLETEARRAY,
    cindex.TypeKind.VARIABLEARRAY,
    cindex.TypeKind.DEPENDENTSIZEDARRAY,
}

POINTER_KIND = cindex.TypeKind.POINTER


def collect_mappings(cursor, mapping):
    if cursor.kind in (cindex.CursorKind.VAR_DECL, cindex.CursorKind.PARM_DECL):
        tkind = cursor.type.kind
        if tkind == POINTER_KIND or tkind in ARRAY_KINDS:
            counter = mapping.setdefault('counter', 0) + 1
            mapping['counter'] = counter
            mapping[cursor.hash] = f"buffer{counter}"
    for child in cursor.get_children():
        collect_mappings(child, mapping)


def get_replacements(tu, mapping):
    repls = []
    for token in tu.get_tokens(extent=tu.cursor.extent):
        if token.kind == cindex.TokenKind.IDENTIFIER:
            cur = token.cursor
            if cur.kind in (cindex.CursorKind.VAR_DECL, cindex.CursorKind.PARM_DECL):
                new = mapping.get(cur.hash) if token.spelling == cur.spelling else None
            else:
                ref = cur.referenced
                new = mapping.get(ref.hash) if ref else None
            if new:
                repls.append((token.extent.start.offset, token.extent.end.offset, new))
    return repls


def apply_replacements(code, repls):
    repls.sort(reverse=True)
    for start, end, text in repls:
        code = code[:start] + text + code[end:]
    return code


def process_code(code, args):
    index = cindex.Index.create()
    tu = index.parse(args.filename, args=['-xc', '-std=c11'], unsaved_files=[(args.filename, code)], options=0)
    mapping = {}
    collect_mappings(tu.cursor, mapping)
    repls = get_replacements(tu, mapping)
    return apply_replacements(code, repls)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('-i', action='store_true', help='overwrite file')
    args = parser.parse_args()
    with open(args.filename, 'r') as f:
        code = f.read()
    new_code = process_code(code, args)
    if args.i:
        with open(args.filename, 'w') as f:
            f.write(new_code)
    else:
        print(new_code)

if __name__ == '__main__':
    main()
