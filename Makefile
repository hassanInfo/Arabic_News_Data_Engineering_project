COMPOSE_FILE_DIR = .

all: 
	@echo "starting services..."
	cd $(COMPOSE_FILE_DIR) && docker-compose --profile all up

up:
	@echo "starting services..."
	cd $(COMPOSE_FILE_DIR) && docker-compose --profile $(PROFILE) up

up_build:
	@echo "Build and starting services..."
	cd $(COMPOSE_FILE_DIR) && docker-compose --profile $(PROFILE) up --build -d

down:
	@echo "Stopping services..."
	cd $(COMPOSE_FILE_DIR) && docker-compose --profile $(PROFILE) down -v

clean:
	@echo "Cleaning up unused Docker resources..."
	docker system prune -f
