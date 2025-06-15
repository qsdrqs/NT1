non_vulnerable_func(E1000ECore *core, const E1000E_RingInfo *r)
{
    return core->mac[r->dh] == core->mac[r->dt];
}
