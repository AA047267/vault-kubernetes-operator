import requests
import jq
import json
import kopf
import logging
import os
import kubernetes.client
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import datetime

logger = logging.getLogger(__name__)

@kopf.timer('stable.example.com', 'v1', 'vaultsyncstatus', interval=60.0)
def vault_sync(body, spec, **kwargs):
    
    name = body['metadata']['name'] 
    target_namespace = spec['deployNamespace']
    target_deployment = spec['deployName']
    secret_engine = spec['secretEngine']
    secret_path = spec['secretPath']
    time_stamp = spec['timeStamp']
    
    
    VAULT_URL = os.environ.get('VAULT_URL')
    url = VAULT_URL + secret_engine +'/metadata/' + secret_path

    with open('/etc/config/VAULT_TOKEN') as token:
        vault_token = token.read().strip()

    headers = {'X-Vault-Token': vault_token}
    resp = requests.get(url, headers=headers)

    filter = jq.compile('.data.updated_time')
    parsed_data = json.loads(resp.content.decode('utf8'))

    updated_time = filter.input(parsed_data).first()
    print(updated_time)


    if time_stamp == updated_time:
        logger.info('Checking for the timestamp in vaultsyncstatus object and updated_time in vault for ' + secret_engine + ' ' + secret_path )
        return {'SyncStatus': 'Already in Sync'}
    else:
        api = kubernetes.client.AppsV1Api()
        api_client = client.ApiClient()
        custom_api = client.CustomObjectsApi(api_client)
        
        try:
            logger.info('Secrets in Vault for ' + secret_engine + ' ' + secret_path + 'have been updated. Triggering rollout for ' + target_deployment )
            deployment_body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": str(datetime.datetime.now())}}}}}
            api.patch_namespaced_deployment(name=target_deployment,namespace=target_namespace,body=deployment_body)
            
            custom_resource_body = {"spec": {"timeStamp": updated_time}}
            custom_api.patch_namespaced_custom_object(group='stable.example.com', version='v1', namespace=target_namespace, plural='vaultsyncstatus', name=name, body=custom_resource_body)
            return {'SyncStatus': 'Synced'}

        except ApiException as e:
            logger.info('Error occured while rolling out for deployment ' + target_deployment + ' Check if deployment exists' )
            print("Exception when calling AppsV1Api->patch_namespaced_deployment_scale")
            return {'SyncStatus': 'Error'}