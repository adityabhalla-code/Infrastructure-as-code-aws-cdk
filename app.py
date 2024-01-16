#!/usr/bin/env python3

import aws_cdk as cdk

from siemens_mlops_cdk.siemens_mlops_cdk_stack import SiemensMlopsCdkStack


app = cdk.App()
SiemensMlopsCdkStack(app, "SiemensMlopsCdkStack")

app.synth()
