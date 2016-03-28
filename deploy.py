#!/usr/bin/python
# -*- coding: utf-8 -*-

from idcf.compute import Compute
c = Compute()
response = c.deployVirtualMachine(
        serviceofferingid='e01a9f32-55c4-4c0d-9b7c-d49a3ccfd3f6',
        templateid='2cafa7ea-56be-45bd-8d21-37f395e36c4e',
        zoneid='a117e75f-d02e-4074-806d-889c61261394',
        name='child',
        )
print response