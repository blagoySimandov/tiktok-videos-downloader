.PHONY: deploy build test clean

# Variables
SERVICE_NAME = prepcart-tiktok-downloader
PROJECT_ID = prepcart-prod
REGION = europe-west1
PORT = 8080
MEMORY = 1Gi
CPU = 1
TIMEOUT = 300
MAX_INSTANCES = 10

# Deploy to Cloud Run
deploy:
	gcloud run deploy $(SERVICE_NAME) \
		--source . \
		--platform managed \
		--region $(REGION) \
		--allow-unauthenticated \
		--port $(PORT) \
		--memory $(MEMORY) \
		--cpu $(CPU) \
		--timeout $(TIMEOUT) \
		--max-instances $(MAX_INSTANCES) \
		--project $(PROJECT_ID)

# Build Docker image locally for testing
build:
	docker build -t $(SERVICE_NAME) .

# Run locally for testing
run-local:
	docker run -p 8080:8080 $(SERVICE_NAME)

# Test the deployed service
test-deployed:
	@echo "Testing health endpoint..."
	curl -X GET https://$(SERVICE_NAME)-$(shell gcloud config get-value project).a.run.app/health

# Clean up local Docker images
clean:
	docker rmi $(SERVICE_NAME) || true
