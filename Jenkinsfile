pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REPO = 'medical-rag-repo'
        IMAGE_TAG = 'latest'
        SERVICE_NAME = 'llmops-medical-service'
        ECS_CLUSTER = 'medical-rag-cluster'
    }

    stages {
        stage('Clone GitHub Repo') {
            steps {
                script {
                    echo 'Cloning GitHub repo to Jenkins...'
                    checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: 'GitHub-Token', url: 'https://github.com/SPaithane1609/Medical-RAG-Chatbot.git']])
                }
            }
        }

        stage('Build, Scan, and Push Docker Image to ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-token']]) {
                    script {
                        def accountId = sh(script: "aws sts get-caller-identity --query Account --output text", returnStdout: true).trim()
                        def ecrUrl = "${accountId}.dkr.ecr.${env.AWS_REGION}.amazonaws.com/${env.ECR_REPO}"
                        def imageFullTag = "${ecrUrl}:${IMAGE_TAG}"

                        sh """
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ecrUrl}
                        docker build -t ${env.ECR_REPO}:${IMAGE_TAG} .
                        trivy image --severity HIGH,CRITICAL --format json -o trivy-report.json ${env.ECR_REPO}:${IMAGE_TAG} || true
                        docker tag ${env.ECR_REPO}:${IMAGE_TAG} ${imageFullTag}
                        docker push ${imageFullTag}
                        """

                        archiveArtifacts artifacts: 'trivy-report.json', allowEmptyArchive: true
                    }
                }
            }
        }

        stage('Deploy to AWS ECS Fargate') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-token']]) {
                    script {
                        echo "Triggering rolling deployment on ECS Cluster: ${ECS_CLUSTER}, Service: ${SERVICE_NAME}..."

                        sh """
                        aws ecs update-service \
                            --cluster ${ECS_CLUSTER} \
                            --service ${SERVICE_NAME} \
                            --force-new-deployment \
                            --region ${AWS_REGION}

                        echo "Waiting for ECS Fargate service to stabilize..."
                        aws ecs wait services-stable \
                            --cluster ${ECS_CLUSTER} \
                            --services ${SERVICE_NAME} \
                            --region ${AWS_REGION}
                        """

                        echo "ECS Fargate deployment completed successfully!"
                    }
                }
            }
        }
    }
}
    
