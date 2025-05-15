targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param srcExists bool
//@secure()
//param srcDefinition object

// @description('Id of the user or app to assign application roles')
// param principalId string

// Tags that should be applied to all resources.
// 
// Note that 'azd-service-name' tags should be applied separately to service host resources.
// Example usage:
//   tags: union(tags, { 'azd-service-name': <service name in azure.yaml> })
var tags = {
  'azd-env-name': environmentName
}

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: '${abbrs.resourcesResourceGroups}-${environmentName}-${resourceToken}'
  location: location
  tags: tags
}

module monitoring './shared/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}-${environmentName}-${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}-${environmentName}-${resourceToken}'
  }
  scope: rg
}

// module dashboard './shared/dashboard-web.bicep' = {
//   name: 'dashboard'
//   params: {
//     name: '${abbrs.portalDashboards}${resourceToken}'
//     applicationInsightsName: monitoring.outputs.applicationInsightsName
//     location: location
//     tags: tags
//   }
//   scope: rg
// }

module registry './shared/registry.bicep' = {
  name: 'registry'
  params: {
    location: location
    tags: tags
    //no dashes (-) in the name as the service dont allow dashes in the name
    name: '${abbrs.containerRegistryRegistries}${environmentName}${resourceToken}'
  }
  scope: rg
}

module openai './shared/openai.bicep' = {
  name: 'openai'
  scope: rg
  params: {
    name: '${abbrs.azureopenai}-${environmentName}-${resourceToken}'
    location: location
  }
}


module documentIntelligence './shared/intelligence.bicep' = {
  name: 'document-intelligence'
  scope: rg
  params: {
    name: '${abbrs.documentintelligence}-${environmentName}-${resourceToken}'
    location: location
  }
}
// module keyVault './shared/keyvault.bicep' = {
//   name: 'keyvault'
//   params: {
//     location: location
//     tags: tags
//     name: '${abbrs.keyVaultVaults}${resourceToken}'
//     principalId: principalId
//   }
//   scope: rg
// }

module appsEnv './shared/apps-env.bicep' = {
  name: 'apps-env'
  params: {
    name: '${abbrs.appManagedEnvironments}-${environmentName}-${resourceToken}'
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
  }
  scope: rg
}



module aiSearch './shared/ai-search.bicep' = {
  name: 'ai-search'
  scope: rg
  params: {
     
    name: '${abbrs.searchSearchServices}-${environmentName}-${resourceToken}'
    location: location
  }
}

module src './app/src.bicep' = {
  name: 'src'
  params: {
    name: '${abbrs.appContainerApps}-${environmentName}-${resourceToken}'
    location: location
    tags: tags
    identityName: '${abbrs.managedIdentityUserAssignedIdentities}src-${resourceToken}'
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    containerAppsEnvironmentName: appsEnv.outputs.name
    containerRegistryName: registry.outputs.name
    exists: srcExists
    //appDefinition: srcDefinition
    appDefinition: {
      settings: [
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: openai.outputs.openAiKey
          secret: true
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openai.outputs.openAiEndpoint
        }
        {
          name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
          value: openai.outputs.chatDeploymentName
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME'
          value: openai.outputs.embeddingDeploymentName
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: '2024-05-01-preview'
        }
        {
          name: 'GLOBAL_LLM_SERVICE'
          value: 'AzureOpenAI'
        }
        {
          name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'
          value: documentIntelligence.outputs.documentIntelligenceEndpoint
        }
        {
          name: 'AZURE_DOC_INTELLIGENCE_KEY'
          value: documentIntelligence.outputs.documentIntelligenceKey
          secret: true
        }
      ]
    }
  }
  dependsOn: [
    openai
    documentIntelligence
    registry
    appsEnv
    monitoring
  ]
  scope: rg
}





output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
//output AZURE_KEY_VAULT_NAME string = keyVault.outputs.name
//output AZURE_KEY_VAULT_ENDPOINT string = keyVault.outputs.endpoint


//openai


output AZURE_OPENAI_ENDPOINT string = openai.outputs.openAiEndpoint
output AZURE_OPENAI_API_KEY string = openai.outputs.openAiKey
output AZURE_OPENAI_CHAT_DEPLOYMENT_NAME string = openai.outputs.chatDeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME string = openai.outputs.embeddingDeploymentName


output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = documentIntelligence.outputs.documentIntelligenceEndpoint
output AZURE_DOC_INTELLIGENCE_KEY string = documentIntelligence.outputs.documentIntelligenceKey
