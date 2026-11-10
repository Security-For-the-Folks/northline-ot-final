# Data Center OT Modbus Lab — convenience targets
COMPOSE=docker compose -f env/docker-compose.yml

up:        ## build + start the lab
	$(COMPOSE) up -d --build
ps:        ## show containers
	$(COMPOSE) ps
logs:      ## follow all logs
	$(COMPOSE) logs -f
toolbox:  ## shell on the IT toolbox host
	docker exec -it toolbox bash
hmi:       ## print the HMI url
	@echo "http://localhost:8080"
reset:     ## restart the drive to normal state
	$(COMPOSE) restart vfd
down:      ## stop + remove
	$(COMPOSE) down
.PHONY: up ps logs toolbox hmi reset down
