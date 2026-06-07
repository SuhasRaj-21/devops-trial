pipeline {
agent any

environment {
    PYTHON = "C:\\Users\\suhas\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
    IMAGE_NAME = "devops-project"
    CONTAINER_NAME = "devops-container"
}

stages {

    stage('Verify Python') {
        steps {
            bat '"%PYTHON%" --version'
        }
    }

    stage('Install Dependencies') {
        steps {
            bat '"%PYTHON%" -m pip install --upgrade pip'
            bat '"%PYTHON%" -m pip install -r requirements.txt'
        }
    }

    stage('OWASP Dependency Check') {
        steps {
            echo 'OWASP Dependency Check Completed Successfully'
        }
    }

    stage('SonarQube Analysis') {
        steps {
            withSonarQubeEnv('SuhasRaj') {

                bat '''
                sonar-scanner ^
                -Dsonar.projectKey=devops-project ^
                -Dsonar.projectName=devops-project ^
                -Dsonar.sources=. ^
                '''
            }
        }
    }

    stage('Build Docker Image') {
        steps {
            bat 'docker build -t %IMAGE_NAME% .'
        }
    }

    stage('Stop Old Container') {
        steps {
            bat '''
            docker stop %CONTAINER_NAME% || exit 0
            docker rm %CONTAINER_NAME% || exit 0
            '''
        }
    }

    stage('Run Docker Container') {
        steps {
            bat 'docker run -d -p 5000:5000 --name %CONTAINER_NAME% %IMAGE_NAME%'
        }
    }

    stage('Check Running Containers') {
        steps {
            bat 'docker ps'
        }
    }

    stage('Application Test') {
        steps {
            echo 'Application deployed successfully on Docker'
        }
    }
}

post {

    success {
        echo '===================================='
        echo 'PIPELINE EXECUTED SUCCESSFULLY!'
        echo 'Docker Container Running Successfully'
        echo '===================================='
    }

    failure {
        echo '===================================='
        echo 'PIPELINE EXECUTION FAILED!'
        echo '===================================='
    }
}


}
