# Pointer/Array Variable Renaming Tool for C Code Snippets

**Goal:**
Uniformly rename all pointer and array variables—including their declarations and all in-scope usages—to sequential names like `buffer1`, `buffer2`, etc., within possibly un-compilable C code fragments, while preserving variable scoping and not affecting unrelated identifiers.

---

## 1. Requirements

| Item               | Description                                                                                                                                                                                                                                                                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Input**          | One or more C code files or snippets. Fragments may be missing headers, macro definitions, type definitions, or even have mild syntax errors.                                                                                                                                                                                                  |
| **Output**         | Code where all pointer and array variables have been renamed in both declarations and all references. Output may overwrite the original file or be written to stdout.                                                                                                                                                                          |
| **Renaming Rules** | - Only pointer (`*`) and array (`[]`) variables are renamed.<br>- Within each lexical scope, variables are sequentially renamed (`buffer1`, `buffer2`, ...).<br>- Shadowed variables in nested scopes are re-numbered appropriately.<br>- All references (usages) in their visible scope are renamed.<br>- Other identifiers are not affected. |
| **Language**       | C and C++ (only for pointer/array renaming).                                                                                                                                                                                                                                                                                     |
| **Robustness**     | Must handle incomplete or erroneous code fragments. Tolerant to missing macros, headers, and type definitions. Should not require a full C compilation.                                                                                                                                                                                                                     |

---

## 2. Challenges

1. **Uncompilable Code Fragments**

   * Missing macros, struct definitions, or headers are common; traditional libclang-based tools may fail or yield incomplete ASTs.
2. **Scope & Shadowing**

   * C allows variable shadowing within inner blocks; renaming must respect lexical scope.
3. **Pointer/Array Identification**

   * Without a type system, pointer/array status must be detected from syntax alone.
4. **Batch/High-Performance Processing**

   * The solution should efficiently handle thousands of fragments in a batch pipeline.

---

## 3. Potential Solution Approaches

| Approach        | Pros                                                      | Cons                                                                                |
| --------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **libclang**    | Precise types, macro expansion, robust for valid code     | Fails on incomplete/uncompilable code, heavyweight dependencies, slower             |
| **tree-sitter** | Fast, lightweight, highly error-tolerant, easy to install | Purely syntactic—requires custom logic to identify pointers/arrays and manage scope |
| **Regex/Lexer** | Fast, trivial install                                     | Extremely error-prone, cannot properly manage scope or complex declarations         |

> **Recommendation:**
> Use [tree-sitter-c](https://github.com/tree-sitter/tree-sitter-c) as the parser. It is error-tolerant, cross-platform, and provides a full syntax tree for C code, even for code fragments that can't be compiled.

---

## 4. Solution Architecture

### 4.1 Dependencies

| Dependency    | Version | Notes                                 |
| ------------- | ------- | ------------------------------------- |
| Python        | ≥3.8    |                                       |
| tree-sitter   | ≥0.21.0 | Install via `pip install tree_sitter` |
| tree-sitter-c | HEAD    | Auto-cloned and compiled on first use |

### 4.2 Directory Structure

```
rename-buffers/
├── README.md
├── requirements.txt
├── rename_buffers.py
└── tests/
    ├── case01_pointer.c
    ├── case02_array.c
    └── ...
```

### 4.3 Core Algorithm

1. **Parse the code using tree-sitter**

   * Build/load a C parser grammar shared library if needed.
   * Parse code fragments with `parser.parse(code_bytes)`.
2. **AST Traversal with Scope Management**

   * Maintain a stack of scopes (for function bodies and compound statements).
   * On a `declaration` or `parameter_declaration`, if it contains a `pointer_declarator` or `array_declarator`, assign the next available `bufferN` name in that scope and record the mapping.
   * For every `identifier` token, if it resolves (by scope chain) to a renamed variable, add it to the replacement list.
3. **Replace in Code**

   * Apply all replacements (using byte offsets) in descending order to prevent offset invalidation.
   * Write the modified code to stdout or overwrite the input file.


---

## 5. Test Cases

| ID  | Code Example                           | What it Tests                |
| --- | -------------------------------------- | ---------------------------- |
| T01 | `int *p; *p = 0;`                      | Simple pointer               |
| T02 | `char buf[10]; buf[1]=0;`              | Simple array                 |
| T03 | `void f(){ int *p; { int *p; *p=0;} }` | Scope shadowing              |
| T04 | `int *p = NULL;`                       | Declaration with initializer |
| T05 | `int *a, b, *c;`                       | Mixed pointer/non-pointer    |
| T06 | `for(int *p=a; p; ++p){}`              | Loop header pointer          |
| T07 | `void g(int *p){ return *p; }`         | Function parameter pointer   |
| T08 | `int arr[2][3]; arr[0][1]=0;`          | Multi-dimensional array      |
| T09 | `{ int *p; *p=0; }`                    | Code block fragment          |
| T10 | `MYARRAY(int, a, 5); a[0]=1;`          | Macro interference           |

**All tests should verify:**

* All pointer/array variable declarations and all in-scope usages are renamed to `bufferN`.
* Non-pointer/array variables remain unchanged.
* Variable shadowing and lexical scope are respected.

### 5.1 Example Test Case (Should be included in `tests/` directory)

```c
non_vulnerable_func(E1000ECore *core, const E1000E_RingInfo *r)
{
    return core->mac[r->dh] == core->mac[r->dt];
}
```

This code should be transformed to:

```c
non_vulnerable_func(E1000ECore *buffer1, const E1000E_RingInfo *buffer2)
{
    return buffer1->mac[buffer2->dh] == buffer1->mac[buffer2->dt];
}
```

### 5.2 Another Example Test Case

```c
PS_SERIALIZER_DECODE_FUNC(php_binary) /* {{{ */
{
	const char *p;
	char *name;
	const char *endptr = val + vallen;
	zval *current;
	int namelen;
	int has_value;
	php_unserialize_data_t var_hash;

	PHP_VAR_UNSERIALIZE_INIT(var_hash);

	for (p = val; p < endptr; ) {
		zval **tmp;
                namelen = ((unsigned char)(*p)) & (~PS_BIN_UNDEF);

                if (namelen < 0 || namelen > PS_BIN_MAX || (p + namelen) >= endptr) {
                        return FAILURE;
                }

		name = estrndup(p + 1, namelen);

		p += namelen + 1;

		if (zend_hash_find(&EG(symbol_table), name, namelen + 1, (void **) &tmp) == SUCCESS) {
			if ((Z_TYPE_PP(tmp) == IS_ARRAY && Z_ARRVAL_PP(tmp) == &EG(symbol_table)) || *tmp == PS(http_session_vars)) {
				efree(name);
				continue;
			}
		}

		if (has_value) {
			ALLOC_INIT_ZVAL(current);
			if (php_var_unserialize(&current, (const unsigned char **) &p, (const unsigned char *) endptr, &var_hash TSRMLS_CC)) {
				php_set_session_var(name, namelen, current, &var_hash  TSRMLS_CC);
			} else {
				PHP_VAR_UNSERIALIZE_DESTROY(var_hash);
				return FAILURE;
			}
			var_push_dtor_no_addref(&var_hash, &current);
		}
		PS_ADD_VARL(name, namelen);
		efree(name);
	}

	PHP_VAR_UNSERIALIZE_DESTROY(var_hash);

	return SUCCESS;
}
/* }}} */
```
This code should be transformed to:

```c
PS_SERIALIZER_DECODE_FUNC(php_binary) /* {{{ */
{
	const char *buffer1;
	char *buffer2;
	const char *buffer3 = val + vallen;
	zval *buffer4;
	int namelen;
	int has_value;
	php_unserialize_data_t var_hash;

	PHP_VAR_UNSERIALIZE_INIT(var_hash);

	for (buffer1 = val; buffer1 < buffer3; ) {
		zval **buffer5;
                namelen = ((unsigned char)(*buffer1)) & (~PS_BIN_UNDEF);

                if (namelen < 0 || namelen > PS_BIN_MAX || (buffer1 + namelen) >= buffer3) {
                        return FAILURE;
                }

		buffer2 = estrndup(buffer1 + 1, namelen);

		buffer1 += namelen + 1;

		if (zend_hash_find(&EG(symbol_table), buffer2, namelen + 1, (void **) &buffer5) == SUCCESS) {
			if ((Z_TYPE_PP(buffer5) == IS_ARRAY && Z_ARRVAL_PP(buffer5) == &EG(symbol_table)) || *buffer5 == PS(http_session_vars)) {
				efree(buffer2);
				continue;
			}
		}

		if (has_value) {
			ALLOC_INIT_ZVAL(buffer4);
			if (php_var_unserialize(&buffer4, (const unsigned char **) &buffer1, (const unsigned char *) buffer3, &var_hash TSRMLS_CC)) {
				php_set_session_var(buffer2, namelen, buffer4, &var_hash  TSRMLS_CC);
			} else {
				PHP_VAR_UNSERIALIZE_DESTROY(var_hash);
				return FAILURE;
			}
			var_push_dtor_no_addref(&var_hash, &buffer4);
		}
		PS_ADD_VARL(buffer2, namelen);
		efree(buffer2);
	}

	PHP_VAR_UNSERIALIZE_DESTROY(var_hash);

	return SUCCESS;
}
```

---

## 6. Usage

```bash
# Print modified code to stdout
python rename_buffers.py mycode.c

# Overwrite original file
python rename_buffers.py mycode.c -i

# Batch process directory
find mydir/ -name '*.c' -print0 | xargs -0 -n1 python rename_buffers.py -i
```

---

## 7. FAQ

| Question                                             | Answer                                                                                       |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Does it support C++?                                 | Yes. C++ support is required also, but also only for pointer/array renaming.                 |
| Will it work with macro-generated pointer variables? | Only if the pointer declarator appears in the actual code; macro expansion is not performed. |
| Will it affect line/column numbers?                  | It will preserve line count; columns may shift if names are of different length.             |

---
