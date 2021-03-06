.PHONY: upload submit user

# folder for the localegarepo
MAIN_REPO=~/csc/dev/LocalEGA-deploy-k8s
# the RSA keys
SSH_KEY_PRIV=$(MAIN_REPO)/auto/config/user.key

USER=ega-box-999
# make sure you have this file or generate a new one
FILE=HG00458.unmapped.ILLUMINA.bwa.CHS.low_coverage.20130415.bam

##############################

DOCKER_PATH=$(MAIN_REPO)
PGP_PUB=$(DOCKER_PATH)/auto/config/key.1.pub
# should be changed with remote ip, this is the default ip for kubernetes
DEPLOY_IP=$(shell minikube ip)
PGP_EMAIL=local-ega@ega.eu
CEGA_PORT=$(shell kubectl describe svc cega-mq --namespace=testing | grep "NodePort:" | awk '$$2=="amqp" {print substr($$3,1,5)}')
INBOX_PORT=$(shell kubectl describe svc inbox --namespace=testing | grep "NodePort:" | awk '{print substr($$3,1,5)}')
#needs the same password that the Lega-MQ conencted to CEGA-MQ
CEGA_PASWORD=$(shell kubectl get secrets cega-connection --namespace=testing -o 'go-template={{index .data "address"}}' | base64 -d | awk '{print substr($$1,13,32)}')
CEGA_MQ_CONNECTION=amqp://lega:$(CEGA_PASWORD)@$(DEPLOY_IP):$(CEGA_PORT)/lega

##############################

all: upload submit

$(FILE).c4ga: $(FILE)
	lega-cryptor encrypt --pk $(PGP_PUB) -i $< -o $@

#	lega-cryptor encrypt -r Sweden -i $< -o $@

upload: $(FILE).c4ga
	chmod 400 $(SSH_KEY_PRIV)
	cd $(<D) && sftp -P $(INBOX_PORT) -i $(SSH_KEY_PRIV) $(USER)@$(DEPLOY_IP) <<< $$"put $(<F)"
	chmod 700 $(SSH_KEY_PRIV)

$(FILE).c4ga.md5: $(FILE).c4ga
	printf '%s' $(shell md5sum $< | cut -d' ' -f1) > $@

$(FILE).md5: $(FILE)
	printf '%s' $(shell md5sum $< | cut -d' ' -f1) > $@

submit: $(FILE).c4ga $(FILE).c4ga.md5 $(FILE).md5
	@echo publish.py --connection amqp://[redacted]@$(lastword $(subst @, ,$(CEGA_MQ_CONNECTION))) $(USER) dir/$(FILE).c4ga --enc ...
	@python publish.py --connection $(subst cega-mq,localhost,$(CEGA_MQ_CONNECTION)) $(USER) $(FILE).c4ga --enc $(shell cat $(FILE).c4ga.md5) --stableID EGAF$(shell cat $(FILE).md5)

clean:
	rm -rf $(FILE).c4ga $(FILE).c4ga.md5 $(FILE).md5
