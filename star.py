#!/usr/bin/python
# -*- coding: utf-8 -*-

from idcf.compute import Compute
c = Compute()
response = c.startVirtualMachine(
        id='0b081d89-adbb-4554-8cd8-5f95564bc018'
        )
print response