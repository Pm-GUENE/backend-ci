pipeline {
    agent any

    environment {
        IMAGE_NAME = 'dentarvd/backend'
    }

    stages {
        stage('Preparation') {
            steps {
                echo 'Preparation de l environnement CI'
                sh '''
                    python3 --version
                    docker --version
                    trivy --version
                    git --version
                '''
            }
        }

        stage('Installation des dependances') {
            steps {
                sh '''
                    python3 -m venv .venv-ci
                    .venv-ci/bin/pip install --upgrade pip
                    .venv-ci/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Tests et couverture') {
            steps {
                sh '''
                    .venv-ci/bin/pytest \
                      --cov=app \
                      --cov-report=term-missing \
                      --cov-fail-under=75
                '''
            }
        }

        stage('Analyse statique Bandit') {
            steps {
                sh '''
                    .venv-ci/bin/bandit -r app -ll
                '''
            }
        }

        stage('Audit des dependances') {
            steps {
                sh '''
                    .venv-ci/bin/pip-audit -r requirements.txt
                '''
            }
        }

        stage('Construction Docker') {
            steps {
                sh '''
                    docker build \
                      -t ${IMAGE_NAME}:${BUILD_NUMBER} \
                      -t ${IMAGE_NAME}:latest .
                '''
            }
        }

        stage('Scan Trivy') {
            steps {
                sh '''
                    trivy image \
                      --severity HIGH,CRITICAL \
                      --exit-code 0 \
                      ${IMAGE_NAME}:${BUILD_NUMBER}

                    trivy image \
                      --severity CRITICAL \
                      --exit-code 1 \
                      ${IMAGE_NAME}:${BUILD_NUMBER}
                '''
            }
        }

        stage('Publication Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKERHUB_USER',
                        passwordVariable: 'DOCKERHUB_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "$DOCKERHUB_TOKEN" | docker login \
                          -u "$DOCKERHUB_USER" --password-stdin

                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest

                        docker logout
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'rm -rf .venv-ci'
            echo 'Fin du pipeline Backend CI'
        }

        success {
            echo 'SUCCESS : backend valide et publie sur Docker Hub'
        }

        failure {
            echo 'FAILURE : verifier les journaux du pipeline'
        }
    }
}
