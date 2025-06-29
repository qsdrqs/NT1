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
