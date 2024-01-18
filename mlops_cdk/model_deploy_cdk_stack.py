from aws_cdk import (
    Stack,
    aws_s3 as s3,
    CfnOutput,
    Duration,
    aws_codecommit as codecommit,
    aws_events as events,
    aws_events_targets as targets,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as pipeline_actions,
    aws_iam as iam,
    RemovalPolicy
)
from constructs import Construct
from aws_cdk.aws_codebuild import BuildEnvironmentVariableType
from aws_cdk.aws_codepipeline import Artifact
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk import CfnParameter


class ModelDeployCiCdStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs)->None:
        super().__init__(scope, id, **kwargs)

        # Parameters
        project_name_param = self.node.try_get_context("SageMakerDeployProjectName")
        print(project_name_param)
        project_id_param = self.node.try_get_context("SageMakerProjectId")
        source_model_package_group_name_param = self.node.try_get_context("SourceModelPackageGroupName")

        # S3 Bucket for Artifacts
        artifacts_bucket = s3.Bucket(self, "MlOpsArtifactsBucket",
                                     bucket_name=f"sagemaker-deploy-project-{project_id_param}",
                                     removal_policy=RemovalPolicy.RETAIN)

        # Reference to an existing CodeCommit Repository for Model Deployment
        model_deploy_repo = codecommit.Repository.from_repository_name(
            self,
            "ModelDeployCodeCommitRepository",
            "sagemaker-siemens-deploy-2-p-k0uqksib99sd-modeldeploy"
        )

        # CodeCommit Repository for Model Deployment
        # model_deploy_repo = codecommit.Repository(self, "ModelDeployCodeCommitRepository",
        #                                           repository_name=f"sagemaker-{project_name_param.value_as_string}-{project_id_param.value_as_string}-modeldeploy",
        #                                           description=f"SageMaker Endpoint deployment infrastructure as code for the Project {project_name_param.value_as_string}")

        # CodeBuild Project for Model Deployment
        model_deploy_build_project = codebuild.Project(self, "ModelDeployBuildProject",
                                                       project_name=f"sagemaker-{project_name_param}-{project_id_param}-modeldeploy",
                                                       description="Builds the Cfn template which defines the Endpoint with specified configuration",
                                                       role=iam.Role(self, "ModelDeployBuildRole",
                                                                             assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                                                             managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")]),
                                                       artifacts=codebuild.Artifacts.s3(
                                                           bucket=artifacts_bucket,
                                                           include_build_id=False,
                                                           package_zip=False,
                                                           path="/model-deploy"
                                                       ),
                                                       environment=codebuild.BuildEnvironment(
                                                           build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_3,
                                                           compute_type=codebuild.ComputeType.SMALL,
                                                           environment_variables={
                                                               'SAGEMAKER_PROJECT_NAME': codebuild.BuildEnvironmentVariable(value=project_name_param, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                               'SAGEMAKER_PROJECT_ID': codebuild.BuildEnvironmentVariable(value=project_id_param, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                               'ARTIFACT_BUCKET': codebuild.BuildEnvironmentVariable(value=artifacts_bucket.bucket_name),
                                                               'MODEL_EXECUTION_ROLE_ARN': codebuild.BuildEnvironmentVariable(value=f"arn:aws:iam::{self.account}:role/service-role/AmazonSageMakerServiceCatalogProductsUseRole"),
                                                               'SOURCE_MODEL_PACKAGE_GROUP_NAME': codebuild.BuildEnvironmentVariable(value=source_model_package_group_name_param, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                               'AWS_REGION': codebuild.BuildEnvironmentVariable(value=self.region),
                                                               'EXPORT_TEMPLATE_NAME': codebuild.BuildEnvironmentVariable(value="template-export.yml"),
                                                               'EXPORT_TEMPLATE_STAGING_CONFIG': codebuild.BuildEnvironmentVariable(value="staging-config-export.json"),
                                                               'EXPORT_TEMPLATE_PROD_CONFIG': codebuild.BuildEnvironmentVariable(value="prod-config-export.json"),
                                                           }),
                                                       source=codebuild.Source.code_commit(repository=model_deploy_repo),
                                                       build_spec=codebuild.BuildSpec.from_source_filename('buildspec.yml')
                                                       )


        # CodeBuild Project for Model Testing
        model_deploy_test_project = codebuild.Project(self, "ModelDeployTestProject",
                                                      project_name=f"sagemaker-{project_name_param}-{project_id_param}-testing",
                                                      description="Test the deployment endpoint",
                                                      role=iam.Role(self, "ModelDeployTestRole",
                                                                            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                                                            managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")]),
                                                      artifacts=codebuild.Artifacts.s3(
                                                          bucket=artifacts_bucket,
                                                          include_build_id=False,
                                                          package_zip=False,
                                                          path="/model-test"
                                                      ),
                                                      environment=codebuild.BuildEnvironment(
                                                          build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_3,
                                                          compute_type=codebuild.ComputeType.SMALL,
                                                          environment_variables={
                                                              'SAGEMAKER_PROJECT_NAME': codebuild.BuildEnvironmentVariable(value=project_name_param, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                              'SAGEMAKER_PROJECT_ID': codebuild.BuildEnvironmentVariable(value=project_id_param, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                              'AWS_REGION': codebuild.BuildEnvironmentVariable(value=self.region),
                                                              'BUILD_CONFIG': codebuild.BuildEnvironmentVariable(value="staging-config-export.json"),
                                                              'EXPORT_TEST_RESULTS': codebuild.BuildEnvironmentVariable(value="test-results.json")
                                                          }),
                                                      source=codebuild.Source.code_commit(repository=model_deploy_repo),
                                                      build_spec=codebuild.BuildSpec.from_source_filename('test/buildspec.yml')
                                                      )

        # CodePipeline for Model Deployment
        source_output = Artifact("SourceOutput")
        build_output = Artifact("BuildOutput")
        model_deploy_pipeline = codepipeline.Pipeline(self, "ModelDeployPipeline",
                                                      pipeline_name=f"sagemaker-{project_name_param}-{project_id_param}-modeldeploy",
                                                      role=iam.Role(self, "ModelDeployPipelineRole",
                                                                    assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
                                                                    managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")]),
                                                      artifact_bucket=artifacts_bucket
                                                      )

        # Add stages to CodePipeline
        model_deploy_pipeline.add_stage(
            stage_name="Source",
            actions=[
                pipeline_actions.CodeCommitSourceAction(
                    action_name="ModelDeployInfraCode",
                    repository=model_deploy_repo,
                    branch="main",
                    output=source_output
                )
            ]
        )

        model_deploy_pipeline.add_stage(
            stage_name="Build",
            actions=[
                pipeline_actions.CodeBuildAction(
                    action_name="BuildDeploymentTemplates",
                    project=model_deploy_build_project,
                    input=source_output,
                    outputs=[build_output],
                    run_order=1
                )
            ]
        )

        # Deploy to Staging Stage
        model_deploy_pipeline.add_stage(
            stage_name="DeployStaging",
            actions=[
                pipeline_actions.CloudFormationCreateUpdateStackAction(
                    action_name="DeployResourcesStaging",
                    template_path=build_output.at_path("template-export.yml"),
                    stack_name=f"sagemaker-{project_name_param}-{project_id_param}-deploy-staging",
                    admin_permissions=True,
                    parameter_overrides={
        # Parameters to override for staging deployment
                    'DataCaptureUploadPath': f"s3://{artifacts_bucket.bucket_name}/data-capture",
                    'ModelPackageName': 'your-model-package-name',
                    'StageName': 'staging',
                    'EndpointInstanceCount': '1',
                    'ModelExecutionRoleArn': 'arn:aws:iam::account-id:role/your-role',
                    'EndpointInstanceType': 'ml.m5.large',
                    'SamplingPercentage': '100',
                    'SageMakerProjectName': project_name_param
                    },
                    extra_inputs=[build_output],
                    run_order=1
                )
            ]
        )

        # Test Staging Stage
        model_deploy_pipeline.add_stage(
            stage_name="TestStaging",
            actions=[
                pipeline_actions.CodeBuildAction(
                    action_name="TestStaging",
                    project=model_deploy_test_project,
                    input=source_output,
                    outputs=[Artifact("TestArtifact")],
                    run_order=2
                )
            ]
        )

        # Manual Approval Stage
        model_deploy_pipeline.add_stage(
            stage_name="ApproveDeployment",
            actions=[
                pipeline_actions.ManualApprovalAction(
                    action_name="ApproveDeployment",
                    run_order=3,
                    additional_information="Approve this model for Production"
                )
            ]
        )

        # Deploy to Production Stage
        model_deploy_pipeline.add_stage(
            stage_name="DeployProd",
            actions=[
                pipeline_actions.CloudFormationCreateUpdateStackAction(
                    action_name="DeployResourcesProd",
                    template_path=build_output.at_path("template-export.yml"),
                    stack_name=f"sagemaker-{project_name_param}-{project_id_param}-deploy-prod",
                    admin_permissions=True,
                    parameter_overrides={
                        # Parameters to override for production deployment
                    },
                    extra_inputs=[build_output],
                    run_order=1
                )
            ]
        )

        # EventBridge Rule for SageMaker Model Package Updates
        model_deploy_sagemaker_event_rule = events.Rule(self, "ModelDeploySageMakerEventRule",
                                                        event_pattern=events.EventPattern(source=["aws.sagemaker"],
                                                                                          detail_type=["SageMaker Model Package State Change"],
                                                                                          detail={"ModelPackageGroupName": [
                                                                                              source_model_package_group_name_param
                                                                                          ],
                                                                                              "ModelApprovalStatus": {"anything-but": ["PendingManualApproval"]}
                                                                                                  }
                                                                                        ),
                                                                                        enabled = True
                                                        )
        # EventBridge Rule for SageMaker Model Package Updates
        model_deploy_sagemaker_event_rule.add_target(targets.CodePipeline(model_deploy_pipeline))

        # EventBridge Rule for CodeCommit Repository Updates
        model_deploy_codecommit_event_rule = events.Rule(self, "ModelDeployCodeCommitEventRule",
                                                         event_pattern=events.EventPattern(
                                                             source=["aws.codecommit"],
                                                             detail_type=["CodeCommit Repository State Change"],
                                                             resources=[model_deploy_repo.repository_arn],
                                                             detail={"referenceType": ["branch"], "referenceName": ["main"]}
                                                         ),
                                                         enabled=True,
                                                         targets=[targets.CodePipeline(model_deploy_pipeline)]
                                                         )

        # Outputs
        CfnOutput(self, "ArtifactsBucketName", value=artifacts_bucket.bucket_name)
        CfnOutput(self, "ModelDeployPipelineName", value=model_deploy_pipeline.pipeline_name)
        CfnOutput(self, "ModelDeployRepoName", value=model_deploy_repo.repository_name)
