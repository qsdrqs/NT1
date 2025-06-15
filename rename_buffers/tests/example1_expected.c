non_vulnerable_func(E1000ECore *buffer1, const E1000E_RingInfo *buffer2)
{
    return buffer1->mac[buffer2->dh] == buffer1->mac[buffer2->dt];
}
