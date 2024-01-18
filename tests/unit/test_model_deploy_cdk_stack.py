import aws_cdk as cdk
from aws_cdk.assertions import Template
from aws_cdk import assertions
from mlops_cdk.model_deploy_cdk_stack import ModelDeployCiCdStack

def test_s3_bucket_created():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    assert template.find_resources("AWS::S3::Bucket")


def test_codecommit_repository_referenced():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    # Assert that a CodeCommit repository is referenced, not created
    template.resource_count_is("AWS::CodeCommit::Repository", 0)

def test_codebuild_projects_created():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    # Assert that two CodeBuild projects are created
    template.resource_count_is("AWS::CodeBuild::Project", 2)

def test_codepipeline_created():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    # Assert that a CodePipeline is created
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

def test_eventbridge_rule_for_sagemaker():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    # Assert that an EventBridge rule for SageMaker is created
    template.has_resource_properties("AWS::Events::Rule", {
        "EventPattern": {
            "source": ["aws.sagemaker"],
            "detail-type": ["SageMaker Model Package State Change"]
        }
    })

def test_eventbridge_rule_for_codecommit():
    # app = cdk.App()
    app = cdk.App(context={"SageMakerProjectId": "test-id", "SageMakerDeployProjectName": "test-project","SourceModelPackageGroupName":"test-model-group"})

    stack = ModelDeployCiCdStack(app, "ModelDeployCiCdStackTest")
    template = assertions.Template.from_stack(stack)

    # Assert that an EventBridge rule for CodeCommit is created
    template.has_resource_properties("AWS::Events::Rule", {
        "EventPattern": {
            "source": ["aws.codecommit"],
            "detail-type": ["CodeCommit Repository State Change"]
        }
    })


