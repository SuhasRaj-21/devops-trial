pipeline {
agent any

environment {
    IMAGE_NAME = "devops-project"
    CONTAINER_NAME = "devops-container"
}

stages {

    stage('Clone Repository') {
        steps {
            echo 'Cloning GitHub repository...'

            git branch: 'main',
            url: 'https://github.com/SuhasRaj-21/dev-ops.git'
        }
    }

    stage('Install Dependencies') {
        steps {
            echo 'Installing Python dependencies...'

            bat 'python -m pip install --upgrade pip'

            bat 'pip install -r requirements.txt'
        }
    }

    stage('Verify Python') {
        steps {
            echo 'Checking Python installation...'

            bat 'python --version'
        }
    }

    stage('Build Docker Image') {
        steps {
            echo 'Building Docker image...'

            bat 'docker build -t %IMAGE_NAME% .'
        }
    }

    stage('Stop Existing Container') {
        steps {
            echo 'Stopping old container if exists...'

            bat 'docker stop %CONTAINER_NAME% || exit 0'

            bat 'docker rm %CONTAINER_NAME% || exit 0'
        }
    }

    stage('Run Docker Container') {
        steps {
            echo 'Running Docker container...'

            bat 'docker run -d -p 5000:5000 --name %CONTAINER_NAME% %IMAGE_NAME%'
        }
    }

    stage('Check Running Containers') {
        steps {
            echo 'Checking Docker containers...'

            bat 'docker ps'
        }
    }
}

post {

    success {
        echo 'CI/CD Pipeline executed successfully!'
    }

    failure {
        echo 'Pipeline failed. Check console output.'
    }
}

}
