#!/bin/bash
#docker rm -f trop_cf_builder
docker-compose down && docker-compose up --force-recreate
docker logs trop_cf_builder > cloudformation.yaml
docker-compose down