pipeline {
    agent {
        label 'rocky'
    }

    parameters {
        string(name: 'DEPOT_RESOURCES_BRANCH', defaultValue: 'main', description: 'Branch of the depot-resources repository to use')
        booleanParam(name: 'DRY_RUN', defaultValue: true, description: 'Run the transformation but do not create a PR')
    }

    environment {
        GITHUB_ORG = "ctrliq"
        GITHUB_REPO = "rlc-cloud-repos"
        PR_BRANCH = "update-azure-mirrors-${BUILD_NUMBER}"
        GITHUB_API = "https://api.github.com"
    }

    stages {
        stage('Setup') {
            steps {
                cleanWs()
                echo "Starting Azure mirrors update pipeline"
                echo "Using depot-resources branch: ${params.DEPOT_RESOURCES_BRANCH}"
            }
        }

        stage('Checkout Repositories') {
            steps {
                echo "Checking out repositories"

                // Create directories for repositories
                sh 'mkdir -p depot-resources rlc-cloud-repos'

                dir('rlc-cloud-repos') {
                    // Checkout the rlc-cloud-repos repository associated with this job
                    checkout scm
                }

                dir('depot-resources') {
                    // Checkout depot-resources repository using scmGit
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: params.DEPOT_RESOURCES_BRANCH]],
                        userRemoteConfigs: [[
                            url: "https://github.com/${GITHUB_ORG}/depot-resources.git",
                            credentialsId: 'cbfeccf2-984b-4ff8-b042-187b73e4d777'
                        ]]
                    ])
                }
            }
        }

        stage('Prepare Environment') {
            steps {
                echo "Preparing environment for transformation"

                // Copy the azure.metadata.yaml file
                sh 'cp depot-resources/azure.metadata.yaml rlc-cloud-repos/'

                // Make sure Python and required packages are available
                sh '''
                    if ! command -v python3 &> /dev/null; then
                        echo "Python3 is not installed"
                        exit 1
                    fi

                    if ! python3 -c "import yaml" &> /dev/null; then
                        echo "Installing PyYAML"
                        pip3 install --user pyyaml
                    fi
                '''
            }
        }

        stage('Transform Configuration') {
            steps {
                dir('rlc-cloud-repos') {
                    echo "Running the transformation script"

                    // Run the transformation script
                    sh 'python3 transform_azure_mirrors.py > new-ciq-mirrors.yaml'
                }
            }
        }

        stage('Check for Changes') {
            steps {
                dir('rlc-cloud-repos') {
                    script {
                        // Compare files to detect changes
                        def hasChanges = sh(
                            script: 'diff -q new-ciq-mirrors.yaml src/rlc_cloud_repos/data/ciq-mirrors.yaml || true',
                            returnStatus: true
                        )

                        // If diff returns 0, files are the same (no changes)
                        // If diff returns 1, files are different (changes exist)
                        if (hasChanges == 1) {
                            echo "Changes detected in mirrors configuration"
                            env.HAS_CHANGES = 'true'
                        } else {
                            echo "No changes detected in mirrors configuration"
                            env.HAS_CHANGES = 'false'
                        }
                    }
                }
            }
        }

        stage('Create Pull Request') {
            when {
                allOf {
                    expression { env.HAS_CHANGES == 'true' }
                    expression { !params.DRY_RUN }
                }
            }
            steps {
                dir('rlc-cloud-repos') {
                    echo "Creating pull request for the changes"

                    // Set up git configuration
                    sh '''
                        git config user.name "Jenkins CI"
                        git config user.email "jenkins@ctrliq.com"
                    '''

                    // Create a new branch
                    sh "git checkout -b ${PR_BRANCH}"

                    // Replace the file
                    sh 'cp new-ciq-mirrors.yaml src/rlc_cloud_repos/data/ciq-mirrors.yaml'

                    // Add and commit changes
                    sh '''
                        git add src/rlc_cloud_repos/data/ciq-mirrors.yaml
                        git commit -m "Update Azure mirrors configuration from depot-resources"
                    '''

                    // Push changes and create PR using the same credentials as used for checkout
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'cbfeccf2-984b-4ff8-b042-187b73e4d777',
                            passwordVariable: 'GITHUB_TOKEN',
                            usernameVariable: 'GITHUB_USER'
                        )
                    ]) {
                        // Push the branch
                        sh """
                            git push https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_ORG}/${GITHUB_REPO}.git ${PR_BRANCH}
                        """

                        // Create the PR using GitHub API
                        sh """
                            curl -X POST \
                                -H "Authorization: token ${GITHUB_TOKEN}" \
                                -H "Accept: application/vnd.github.v3+json" \
                                ${GITHUB_API}/repos/${GITHUB_ORG}/${GITHUB_REPO}/pulls \
                                -d '{
                                    "title": "Update Azure mirrors configuration",
                                    "body": "Automated update of Azure mirrors configuration from latest depot-resources metadata.",
                                    "head": "${PR_BRANCH}",
                                    "base": "main"
                                }'
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline completed"

            script {
                if (env.HAS_CHANGES == 'true') {
                    if (params.DRY_RUN) {
                        echo "Changes were detected, but no PR was created (dry run mode)"
                    } else {
                        echo "Changes were detected and a PR was created"
                    }
                } else {
                    echo "No changes were detected in the Azure mirrors configuration"
                }
            }
        }
        success {
            echo "Pipeline succeeded"
        }
        failure {
            echo "Pipeline failed. Please check the logs for details."
        }
        cleanup {
            cleanWs()
        }
    }
}

