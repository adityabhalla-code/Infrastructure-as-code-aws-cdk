import aws_cdk as cdk
from aws_cdk.assertions import Template
from mlops_cdk.model_training_cdk_stack import ModelTrainingCiCdStack


def test_s3_bucket_created():
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerProjectName": "test-project"})
    stack = ModelTrainingCiCdStack(app, "ModelTrainingCiCdStack")
    template = Template.from_stack(stack)

    # Check if an S3 bucket is created
    template.resource_count_is("AWS::S3::Bucket", 2)

def test_codebuild_project_created():
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerProjectName": "test-project"})
    stack = ModelTrainingCiCdStack(app, "ModelTrainingCiCdStack")
    template = Template.from_stack(stack)

    # Check if a CodeBuild project is created
    template.resource_count_is("AWS::CodeBuild::Project", 1)

def test_codepipeline_created():
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerProjectName": "test-project"})
    stack = ModelTrainingCiCdStack(app, "ModelTrainingCiCdStack")
    template = Template.from_stack(stack)

    # Check if a CodePipeline pipeline is created
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

def test_iam_roles_created():
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerProjectName": "test-project"})
    stack = ModelTrainingCiCdStack(app, "ModelTrainingCiCdStack")
    template = Template.from_stack(stack)

    # Check if IAM roles are created
    template.resource_count_is("AWS::IAM::Role", 5)
