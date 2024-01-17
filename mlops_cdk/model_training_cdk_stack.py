from aws_cdk import Stack, aws_s3 as s3, CfnOutput , Duration, aws_codecommit as codecommit, aws_events as events, aws_events_targets as targets, aws_codebuild as codebuild, aws_codepipeline as codepipeline, aws_codepipeline_actions as pipeline_actions, aws_iam as iam
from aws_cdk import RemovalPolicy
from constructs import Construct
from aws_cdk.aws_codebuild import BuildEnvironmentVariableType
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk.aws_codepipeline import Artifact
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
import uuid
class ModelTrainingCiCdStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a role for CodeBuild
        codebuild_role = iam.Role(
            self, "CodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com")
        )

        # Attach the AmazonEC2ContainerRegistryReadOnly managed policy
        codebuild_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
        )

        # Reference the ECR repository
        ecr_repo = ecr.Repository.from_repository_arn(
            self,
            "MyEcrRepo",
            "arn:aws:ecr:us-east-1:644383320443:repository/python-311-image-repo"
        )

        # Define the code commit repository
        source_repo = codecommit.Repository.from_repository_name(
            self, "SourceRepo", "sagemaker-siemens-build-01-16-06-51-43-p-oldzx0zjfxee-modelbuild")

        # Parameters
        project_name = self.node.try_get_context("SageMakerProjectName")
        project_id = self.node.try_get_context("SageMakerProjectId")
        # if not project_id:
        #     project_id = str(uuid.uuid4())

        # Resources
        # S3 Bucket
        artifacts_bucket = s3.Bucket(self, "MlOpsArtifactsBucket",
                                     bucket_name=f"sagemaker-project-{project_id}",
                                     removal_policy=RemovalPolicy.RETAIN)

        # # CodeCommit Repository
        # model_build_repo = codecommit.Repository(self, "ModelBuildCodeCommitRepository",
        #                                          repository_name=f"sagemaker-{project_name}-{project_id}-modelbuild",
        #                                          description=f"SageMaker Model building workflow infrastructure as code for the Project {project_name}")

        # Events Rule
        code_commit_rule = events.Rule(self, "ModelBuildCodeCommitEventRule",
                                       event_pattern=events.EventPattern(
                                           source=["aws.codecommit"],
                                           detail_type=["CodeCommit Repository State Change"],
                                           resources=[source_repo.repository_arn],
                                           detail={"referenceType": ["branch"], "referenceName": ["main"]}),
                                       enabled=True,
                                       description="Rule to trigger a deployment when ModelBuild CodeCommit repository is updated")


        # Define the CodePipeline source action using the existing repository
        # source_action = codepipeline_actions.CodeCommitSourceAction(
        #     action_name="CodeCommit_Source",
        #     repository=source_repo,
        #     branch="main",  # Make sure this is the correct branch name
        #     output=codepipeline.Artifact("SourceArtifact")
        # )
        # CodeBuild Project
        code_build_project = codebuild.Project(self, "SageMakerModelPipelineBuildProject",
                                              project_name=f"sagemaker-{project_name}-{project_id}-modelbuild",
                                              description="Builds the model building workflow code repository, creates the SageMaker Pipeline and executes it",
                                              environment=codebuild.BuildEnvironment(
                                                  build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                                                  # # build_image=codebuild.LinuxBuildImage.from_code_build_image_id(
                                                  # #   "aws/codebuild/amazonlinux-x86_64-lambda-standard:python3.11"),
                                                  # build_image=codebuild.LinuxBuildImage.from_ecr_repository(
                                                  #     ecr_repo,
                                                  #     "latest"  # Tag of your image in ECR
                                                  # ),
                                                  # privileged=True,
                                                  compute_type=codebuild.ComputeType.LARGE,
                                                  environment_variables={
                                                      'SAGEMAKER_PIPELINE_ROLE_ARN': codebuild.BuildEnvironmentVariable(
                                                          value='arn:aws:iam::644383320443:role/service-role/AmazonSageMakerServiceCatalogProductsExecutionRole',type=BuildEnvironmentVariableType.PLAINTEXT),
                                                      'SAGEMAKER_PROJECT_NAME': codebuild.BuildEnvironmentVariable(value=project_name, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                      'SAGEMAKER_PROJECT_ID': codebuild.BuildEnvironmentVariable(value=project_id, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                      'ARTIFACT_BUCKET': codebuild.BuildEnvironmentVariable(value=artifacts_bucket.bucket_name, type=BuildEnvironmentVariableType.PLAINTEXT),
                                                      'SAGEMAKER_PIPELINE_NAME': codebuild.BuildEnvironmentVariable(value=f"sagemaker-{project_name}", type=BuildEnvironmentVariableType.PLAINTEXT),
                                                      'AWS_REGION': codebuild.BuildEnvironmentVariable(value=self.region, type=BuildEnvironmentVariableType.PLAINTEXT)
                                                  }),
                                              source=codebuild.Source.code_commit(repository=source_repo),
                                              build_spec=codebuild.BuildSpec.from_source_filename('codebuild-buildspec.yml'),
                                              timeout=Duration.minutes(480),
                                              role=iam.Role(self, "CodeBuildServiceRole",
                                                            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                                            managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")]
                                                            )
                                              )

        # IAM Role for CodePipeline
        pipeline_role = iam.Role(self, "CodePipelineRole",
                                 assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
                                 managed_policies=[ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")])

        # CodePipeline
        model_build_pipeline = codepipeline.Pipeline(self, "ModelBuildPipeline",
                                                     pipeline_name=f"sagemaker-{project_name}-{project_id}-modelbuild",
                                                     role=pipeline_role,
                                                     artifact_bucket=artifacts_bucket,
                                                     stages=[
                                                         codepipeline.StageProps(
                                                             stage_name="Source",
                                                             actions=[
                                                                 pipeline_actions.CodeCommitSourceAction(
                                                                     action_name="ModelBuildWorkflowCode",
                                                                     repository=source_repo,
                                                                     branch="main",
                                                                     output=Artifact("SourceOutput")
                                                                 )
                                                             ]
                                                         ),
                                                         codepipeline.StageProps(
                                                             stage_name="Build",
                                                             actions=[
                                                                 pipeline_actions.CodeBuildAction(
                                                                     action_name="BuildAndExecuteSageMakerPipeline",
                                                                     project=code_build_project,
                                                                    input=Artifact("SourceOutput"),
                                                                    outputs=[Artifact("BuildOutput")],
                                                                    run_order=1
                                                                    )
                                                                ]
                                                            )
                                                        ])
        # Add target to the rule
        code_commit_rule.add_target(targets.CodePipeline(model_build_pipeline))

        # Outputs (optional)
        CfnOutput(self, "ArtifactsBucketName", value=artifacts_bucket.bucket_name)
        # CfnOutput(self, "ModelBuildRepoName", value=model_build_repo.repository_name)
        CfnOutput(self, "ModelBuildPipelineName", value=model_build_pipeline.pipeline_name)
        CfnOutput(self, "SourceRepoName", value=source_repo.repository_name)