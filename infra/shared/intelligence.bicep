param name string
param location string

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'FormRecognizer' // 👈 Important: Document Intelligence uses FormRecognizer kind
  sku: {
    name: 'S0'
  }
  properties: {
    apiProperties: {
      apiKind: 'DocumentIntelligence'
    }
    customSubDomainName: name  // 👈 THIS forces custom endpoint domain
    publicNetworkAccess: 'Enabled'
  }
}

output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint
output documentIntelligenceKey string = listKeys(documentIntelligence.id, documentIntelligence.apiVersion).key1
