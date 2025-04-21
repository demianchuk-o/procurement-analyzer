PROJECT_NAME := integration_tests

INTEGRATION_TEST_COMMAND := docker-compose -p $(PROJECT_NAME) -f docker-compose.yml -f docker-compose.integration.yml up --build --exit-code-from test

integration-test:
	@echo "Starting integration tests..."
	$(INTEGRATION_TEST_COMMAND)
	@echo "Integration tests finished."

integration-clean:
	@echo "Cleaning up integration test environment..."
	docker-compose -p $(PROJECT_NAME) -f docker-compose.yml -f docker-compose.integration.yml down -v --remove-orphans
	@echo "Clean up complete."

.DEFAULT_GOAL := integration-test