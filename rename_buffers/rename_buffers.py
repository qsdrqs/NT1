import argparse
import sys
from typing import List, Tuple

from tree_sitter import Language, Parser
import tree_sitter_c


def _build_parser() -> Parser:
    parser = Parser()
    parser.language = Language(tree_sitter_c.language())
    return parser


def _find_identifier(node):
    if node.type == "identifier":
        return node
    for child in node.children:
        result = _find_identifier(child)
        if result:
            return result
    return None


def _contains_ptr_or_array(node) -> bool:
    if node.type in {"pointer_declarator", "array_declarator"}:
        return True
    for child in node.children:
        if _contains_ptr_or_array(child):
            return True
    return False


class _Scope:
    def __init__(self):
        self.map = {}

    def add(self, name: str, counter_cb) -> str:
        new_index = counter_cb()
        new = f"buffer{new_index}"
        self.map[name] = new
        return new


class _Renamer:
    def __init__(self, code: bytes):
        self.code = code
        self.parser = _build_parser()
        self.tree = self.parser.parse(code)
        self.replacements: List[Tuple[int, int, str]] = []
        self.decl_nodes = set()
        self.scopes = [_Scope()]
        self._counter = 0

        # handle function definitions missing a return type
        self._maybe_fix_missing_type()

    def rename(self) -> bytes:
        if self.tree is not None:
            self._traverse(self.tree.root_node)
        result = bytearray(self.code)
        for start, end, text in sorted(self.replacements, key=lambda x: -x[0]):
            result[start:end] = text.encode()
        return bytes(result)

    # Utility functions
    def _lookup(self, name: str):
        for scope in reversed(self.scopes):
            if name in scope.map:
                return scope.map[name]
        return None

    def _push_scope(self):
        self.scopes.append(_Scope())

    def _pop_scope(self):
        self.scopes.pop()

    def _next_index(self):
        self._counter += 1
        return self._counter

    def _maybe_fix_missing_type(self):
        root = self.tree.root_node
        if root.type != "translation_unit" or root.named_child_count < 2:
            return
        first = root.named_child(0)
        second = root.named_child(1)
        if (
            first.type == "expression_statement"
            and second.type == "compound_statement"
        ):
            call = first.child(0)
            if call and call.type == "call_expression":
                args = call.child_by_field_name("arguments")
                if args:
                    self._push_scope()
                    self._process_param_text(args)
                    self._traverse(second)
                    self._pop_scope()
                    # skip normal traversal
                    self.tree = None

    # Traversal
    def _traverse(self, node):
        t = node.type
        if t == "function_definition":
            self._push_scope()
            decl = node.child_by_field_name("declarator")
            if decl is not None:
                self._process_function_declarator(decl)
            body = node.child_by_field_name("body")
            if body:
                self._traverse(body)
            self._pop_scope()
            return
        if t == "compound_statement":
            self._push_scope()
            for child in node.children:
                self._traverse(child)
            self._pop_scope()
            return
        if t == "for_statement":
            self._push_scope()
            for field in ["initializer", "condition", "update", "body"]:
                c = node.child_by_field_name(field)
                if c:
                    self._traverse(c)
            self._pop_scope()
            return
        if t == "declaration":
            for child in node.named_children:
                if child.type in {"init_declarator", "identifier"}:
                    decl = child.child_by_field_name("declarator") or child
                    self._process_declarator(decl)
                elif child.type in {"pointer_declarator", "array_declarator", "parenthesized_declarator"}:
                    self._process_declarator(child)
                else:
                    self._traverse(child)
            return
        if t == "parameter_declaration":
            decl = node.child_by_field_name("declarator")
            if decl:
                self._process_declarator(decl)
            return
        if t == "identifier":
            if node.id in self.decl_nodes:
                return
            name = self.code[node.start_byte:node.end_byte].decode()
            new = self._lookup(name)
            if new:
                self.replacements.append((node.start_byte, node.end_byte, new))
            return
        for child in node.children:
            self._traverse(child)

    def _process_declarator(self, decl):
        id_node = _find_identifier(decl)
        if not id_node:
            return
        if _contains_ptr_or_array(decl):
            old = self.code[id_node.start_byte:id_node.end_byte].decode()
            new = self.scopes[-1].add(old, self._next_index)
            self.decl_nodes.add(id_node.id)
            self.replacements.append((id_node.start_byte, id_node.end_byte, new))
        for child in decl.children:
            self._traverse(child)

    def _process_function_declarator(self, decl):
        params = decl.child_by_field_name("parameters")
        if params:
            for param in params.named_children:
                if param.type == "parameter_declaration":
                    d = param.child_by_field_name("declarator")
                    if d:
                        self._process_declarator(d)
        # process body declarator children besides parameters
        for child in decl.children:
            if child is not params:
                self._traverse(child)

    def _process_param_text(self, node):
        import re
        text = self.code[node.start_byte : node.end_byte].decode()
        content = text[1:-1]
        offset = node.start_byte + 1
        for m in re.finditer(r'\*\s*([A-Za-z_][A-Za-z0-9_]*)', content):
            name = m.group(1)
            start = offset + m.start(1)
            end = start + len(name)
            new = self.scopes[-1].add(name, self._next_index)
            self.replacements.append((start, end, new))
        for m in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*\[', content):
            name = m.group(1)
            start = offset + m.start(1)
            end = start + len(name)
            new = self.scopes[-1].add(name, self._next_index)
            self.replacements.append((start, end, new))


def rename_code(code: str) -> str:
    bytes_code = code.encode() if isinstance(code, str) else code
    new = _Renamer(bytes_code).rename()
    return new.decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("-i", action="store_true", help="edit in place")
    args = ap.parse_args()
    data = open(args.file, "rb").read()
    output = _Renamer(data).rename()
    if args.i:
        with open(args.file, "wb") as f:
            f.write(output)
    else:
        sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
