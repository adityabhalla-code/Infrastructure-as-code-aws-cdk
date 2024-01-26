#!/usr/bin/env python3

import aws_cdk as cdk

from mlops_cdk.model_training_cdk_stack import ModelTrainingCiCdStack
from mlops_cdk.model_deploy_cdk_stack import ModelDeployCiCdStack

app = cdk.App()
# Create the Model Training CI/CD Stack
# ModelTrainingCiCdStack(app, "SiemensMlopsCdkStack")
# Create the Model Deployment CI/CD Stack
ModelDeployCiCdStack(app, "SiemensMlopsDeploymentCdkStack")
app.synth()
