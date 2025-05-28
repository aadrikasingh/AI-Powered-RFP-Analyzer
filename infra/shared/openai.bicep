param name string
param location string

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    apiProperties: {
      kind: 'OpenAI'
    }
    customSubDomainName: name 
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4Deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      name: 'gpt-4o'
      version: '2024-11-20'
      format: 'OpenAI'
    }
    raiPolicyName: 'Microsoft.Default'
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'text-embedding-ada-002'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      name: 'text-embedding-ada-002'
      version: '2' // Correct version for embeddings
      format: 'OpenAI'
    }
    raiPolicyName: 'Microsoft.Default'
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  dependsOn: [
    gpt4Deployment
  ]
}

output openAiEndpoint string = openai.properties.endpoint
output openAiKey string = listKeys(openai.id, openai.apiVersion).key1
output chatDeploymentName string = gpt4Deployment.name
output embeddingDeploymentName string = embeddingDeployment.name

