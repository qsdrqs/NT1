import argparse
import re
from clang import cindex

ARRAY_KINDS = {
    cindex.TypeKind.CONSTANTARRAY,
    cindex.TypeKind.INCOMPLETEARRAY,
    cindex.TypeKind.VARIABLEARRAY,
    cindex.TypeKind.DEPENDENTSIZEDARRAY,
}
POINTER_KIND = cindex.TypeKind.POINTER


def rename_in_function(func_cursor, code, mapping):
    start = func_cursor.extent.start.offset
    end = func_cursor.extent.end.offset
    body = code[start:end]
    for old, new in mapping.items():
        body = re.sub(r"\b" + re.escape(old) + r"\b", new, body)
    return code[:start] + body + code[end:]


def process(code, filename):
    index = cindex.Index.create()
    tu = index.parse(filename, args=['-xc'], unsaved_files=[(filename, code)], options=0)
    for cursor in tu.cursor.get_children():
        if cursor.kind == cindex.CursorKind.FUNCTION_DECL:
            mapping = {}
            counter = 1
            for param in cursor.get_arguments():
                t = param.type.kind
                if t == POINTER_KIND or t in ARRAY_KINDS:
                    mapping[param.spelling] = f"buffer{counter}"
                    counter += 1
            if mapping:
                code = rename_in_function(cursor, code, mapping)
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('filename')
    ap.add_argument('-i', action='store_true')
    args = ap.parse_args()
    with open(args.filename) as f:
        code = f.read()
    new_code = process(code, args.filename)
    if args.i:
        with open(args.filename, 'w') as f:
            f.write(new_code)
    else:
        print(new_code)

if __name__ == '__main__':
    main()
