[![Build Status](https://travis-ci.org/NBISweden/LocalEGA-deploy-k8s.svg?branch=master)](https://travis-ci.org/NBISweden/LocalEGA-deploy-k8s)

## LocalEGA Kubernetes Deployment

#### Table of Contents
- [Deployment via Python Script](#deployment-via-python-script)
	- [Generating Configuration](#generating-configuration)
- [Deployment from YAML files](#deployment-from-yaml-files)
	- [Deploy Fake CEGA](#deploy-fake-cega)
	- [Deploy LocalEGA](#deploy-localega)
	- [Other useful information](#other-useful-information)
- [Deployment for OpenShift](#deployment-for-openshift)
- [Testing](#testing)



### Deployment via Python Script

We provide an python script based on https://github.com/kubernetes-client/python that sets up all the necessary configuration (e.g. generating keys, certificates, configuration files etc.) and pods along with necessary services and volumes.
The script is intended to work both with a minikube or any Kubernetes cluster, provided the user has an API key.

**NOTE: Requires Python >3.6.**

The script is in `auto` folder and can be run as:
```
cd ~/LocalEGA/deployments/kube/auto
pip install -r requirements.txt
python deploy.py --config
python deploy.py --fake-cega --deploy
```

In the `deploy.py` service/pods names and other parameters should be configured:
```json
_localega = {"role": "LocalEGA",
             "email": "test@csc.fi",
             "services": {"keys": "keys",
                          "inbox": "inbox",
                          "ingest": "ingest",
                          "s3": "minio",
                          "broker": "mq",
                          "db": "db",
                          "verify": "verify"},
             "key": {"name": "Test PGP",
                     "comment": "Some comment",
                     "expire": "30/DEC/19 08:00:00",
                     "id": "key.1"},
             "ssl": {"country": "Finland",
                     "country_code": "FI",
                     "location": "Espoo", "org": "CSC"},
             "cega": {"user": "lega",
                      "endpoint": "http://cega-users.testing:8001/user/"}
}
```

Using the deploy script:
```
╰─$ python deploy.py --help
Usage: deploy.py [OPTIONS]

  Local EGA deployment script.

Options:
  --config            Flag for generating configuration if does not exist, or
                      generating a new one.
  --config-path TEXT  Specify base path for the configuration directory.
  --deploy            Deploying the configuration secrets and pods.
  --ns TEXT           Deployment namespace, defaults to "testing".
  --cega-mq TEXT      CEGA MQ IP, for fake default "cega-mq".
  --cega-pwd TEXT     CEGA MQ Password, for fake CEGA MQ it is set up with a
                      default.
  --cega-api TEXT     CEGA User endpoint, default http://cega-
                      users.testing:8001/user/.
  --key-pass TEXT     CEGA Users RSA key password.
  --fake-cega         Deploy fake CEGA.
  --help              Show this message and exit.
```

#### Generating Configuration

In order to generate just the configuration files and parameters,
independently of starting a deployment or not, we can use the script as follows :

```console
python deploy --config
python deploy.py --config --cega-mq <mq_ip> --cega-pwd <mq_pass> --cega-api <user-endpoint>
```
By default configuration is generated in `auto/config` folder, in order to specify a path for the configuration directory use:
```
python deploy.py --config --config-path <path>
```
Generated `config` directory files:
```
config
├── cega.config
├── cega.json
├── conf.ini
├── defs.json
├── key.1.pub
├── key.1.sec
├── keys.ini
├── rabbitmq.config
├── ssl.cert
├── ssl.key
├── trace.ini
└── user.key
```
Parameters generated in `trace.ini` file.
```
[PARAMETERS]
cega_mq_pass =
cega_address =
cega_user_public_key =
cega_key_password =
cega_user_endpoint =
cega_creds =
mq_password =
postgres_password =
s3_access =
s3_secret =
lega_password =
keys_password =
```

### Deployment from YAML files

The YAML files (from the `yml` directory) represent vanilla deployment setup configuration for LocalEGA, configuration that does not include configuration/passwords for starting services. Such configuration can generated using the `make bootstrap` script in the `~/LocalEGA/deployment/docker` folder or provided per each case. The YAML file only provide base `hostPath` volumes, for other volume types check [Kubernetes Volumes](https://kubernetes.io/docs/concepts/storage/volumes/).

Files that require configuration:
* `data-in/keys/cm.keyserver.yml`
* `data-in/keys/secret.keyserver.yml`
* `data-in/lega-config/cm.lega.yml`
* `data-in/lega-config/secret.lega.yml`

When generating secrets from command line follow the instructions at [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) and use:
```
$ echo -n 'secret' | base64
```

Following instructions are for Minikube deployment:
Once [minikube](https://kubernetes.io/docs/tasks/tools/install-minikube/) and [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) are installed:

```
cd ~/LocalEGA/deployment/kube/yml
minikube start
kubectl create namespace localega
```
#### Deploy Fake CEGA

CEGA Broker is available for now and its address needs to be setup LocalEGA broker in `amqp://<user>:<password>@<cega-ip>:5672/<queue>`
The `<cega-ip>` is the IP of the Kubernetes Pod for CEGA Broker.
```
kubectl create -f ./cega-mq --namespace=localega
```
CEGA Users requires the setting up a user `ega-box-999` with a public SSH RSA key and added to the `yml/cega-users/cm.cega.yml` line 153.
After that it can be started using

```
kubectl create -f ./cega-users --namespace=localega
```

####  Deploy LocalEGA
```
kubectl create -f ./data-in/lega-config --namespace=localega
kubectl create -f ./data-in/mq -f ./data-in/postgres -f ./data-in/s3 --namespace=localega
kubectl create -f ./data-in/keys -f ./data-in/verify -f ./data-in/ingest -f ./data-in/inbox --namespace=localega
```

#### Other useful information

* See minikube services: `minikube service list`
* Delete services: `kubectl delete -f ./data-in/keys`
* Working with [volumes in Minio](https://vmware.github.io/vsphere-storage-for-kubernetes/documentation/minio.html)

### Deployment for OpenShift

The files provided in the `yml` directory can be reused for deployment to OpenShift with some changes:
- Minio requires `10Gi` volume to start properly in Openshift, although in minikube it it seems to do by with just 0.5Gi.
- By default, OpenShift Origin runs containers using an arbitrarily assigned user ID as per [OpenShift Guidelines](https://docs.openshift.org/latest/creating_images/guidelines.html#openshift-specific-guidelines), thus using `gosu` command for changing user is not allowed. The command for keyserver would look like `["ega-keyserver","--keys","/etc/ega/keys.ini"]` instead of `["gosu","lega","ega-keyserver","--keys","/etc/ega/keys.ini"]`.

* Postgres DB requires a different container therefore we provided a different YAML configuration file for it in the [`oc/postgres` directory](oc/postgres), also the volume attached to Postgres DB needs `ReadWriteMany` permissions.
* Keyserver requires different configuration therefore we provided a different YAML configuration file for it in the [`oc/keys` directory](oc/keys).
* Inbox requires different configuration therefore we provided a different YAML configuration file for it in the [`oc/inbox` directory](oc/inbox).

### Testing

Information about testing is available in [testing directory](test). We recommend using Version 2 with the `sftp.py`
