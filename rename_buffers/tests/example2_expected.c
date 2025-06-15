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
/* }}} */
