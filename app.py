#!/usr/bin/env python3

import aws_cdk as cdk

from mlops_cdk.model_training_cdk_stack import ModelTrainingCiCdStack


app = cdk.App()
ModelTrainingCiCdStack(app, "SiemensMlopsCdkStack")

app.synth()
