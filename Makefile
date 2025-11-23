.PHONY: 
	help 
	install

## help: print this help message
help:
	@echo 'Usage:'
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' | sed -e 's/^/ /'
	
install:
	pip install -r requirements/base.txt
	pip install --no-deps -r requirements/git.txt

reinstall-proto:
	pip install --force-reinstall --no-deps -r requirements/git.txt

