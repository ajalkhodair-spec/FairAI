targetScope = 'resourceGroup'

@description('Azure region for all experiment resources.')
param location string = resourceGroup().location

@description('Short lowercase deployment identifier.')
@minLength(3)
@maxLength(12)
param deploymentName string = 'fairai'

@description('Temporary non-burstable VM size.')
param vmSize string = 'Standard_D2s_v5'

@description('Linux administrator username.')
param adminUsername string = 'fairaiadmin'

@secure()
@description('OpenSSH public key. Password authentication is disabled.')
param adminSshPublicKey string

@description('Single trusted IPv4 CIDR allowed to SSH, for example 203.0.113.10/32.')
param adminSourceCidr string

@description('Daily automatic shutdown time in HHmm format.')
param shutdownTime string = '2300'

@allowed([
  'Arab Standard Time'
  'UTC'
])
param shutdownTimeZone string = 'Arab Standard Time'

param tags object = {
  project: 'FairAI'
  environment: 'major-revision-experiment'
  owner: 'research'
  costControl: 'auto-shutdown'
}

var roles = [
  'controller'
  'worker1'
  'worker2'
]
var subnetPrefix = '10.42.0.0/24'

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: '${deploymentName}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
  }
}

resource computeSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' = {
  parent: vnet
  name: 'compute'
  properties: {
    addressPrefix: subnetPrefix
    networkSecurityGroup: {
      id: nsg.id
    }
    serviceEndpoints: [
      {
        service: 'Microsoft.Storage'
      }
    ]
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: '${deploymentName}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowSshFromAdmin'
        properties: {
          priority: 100
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: adminSourceCidr
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'AllowExperimentVnet'
        properties: {
          priority: 110
          access: 'Allow'
          direction: 'Inbound'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
    ]
  }
}

resource publicIps 'Microsoft.Network/publicIPAddresses@2024-01-01' = [for role in roles: {
  name: '${deploymentName}-${role}-pip'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    idleTimeoutInMinutes: 10
  }
}]

resource nics 'Microsoft.Network/networkInterfaces@2024-01-01' = [for (role, index) in roles: {
  name: '${deploymentName}-${role}-nic'
  location: location
  tags: tags
  properties: {
    enableAcceleratedNetworking: true
    ipConfigurations: [
      {
        name: 'primary'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: computeSubnet.id
          }
          publicIPAddress: {
            id: publicIps[index].id
          }
        }
      }
    ]
  }
}]

resource vms 'Microsoft.Compute/virtualMachines@2024-03-01' = [for (role, index) in roles: {
  name: '${deploymentName}-${role}'
  location: location
  tags: union(tags, { role: role })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    osProfile: {
      computerName: '${deploymentName}-${role}'
      adminUsername: adminUsername
      customData: base64(loadTextContent('cloud-init.yaml'))
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        patchSettings: {
          patchMode: 'AutomaticByPlatform'
          assessmentMode: 'AutomaticByPlatform'
        }
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminSshPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        diskSizeGB: 64
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
        deleteOption: 'Delete'
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nics[index].id
          properties: {
            deleteOption: 'Delete'
          }
        }
      ]
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}]

resource shutdownSchedules 'Microsoft.DevTestLab/schedules@2018-09-15' = [for (role, index) in roles: {
  name: 'shutdown-computevm-${vms[index].name}'
  location: location
  tags: tags
  properties: {
    status: 'Enabled'
    taskType: 'ComputeVmShutdownTask'
    dailyRecurrence: {
      time: shutdownTime
    }
    timeZoneId: shutdownTimeZone
    notificationSettings: {
      status: 'Disabled'
    }
    targetResourceId: vms[index].id
  }
}]

resource resultsStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take('${deploymentName}${uniqueString(resourceGroup().id)}', 24)
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: computeSubnet.id
          action: 'Allow'
        }
      ]
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: resultsStorage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}

resource resultsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'results'
  properties: {
    publicAccess: 'None'
  }
}

resource storageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (role, index) in roles: {
  name: guid(resultsStorage.id, vms[index].id, 'blob-contributor')
  scope: resultsStorage
  properties: {
    principalId: vms[index].identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
  }
}]

output topology object = {
  logicalClientCounts: [5, 10, 20]
  physicalHosts: length(roles)
  roles: roles
  vmSize: vmSize
}
output publicIpAddresses array = [for (role, index) in roles: {
  role: role
  vmName: vms[index].name
  ipAddress: publicIps[index].properties.ipAddress
}]
output privateIpAddresses array = [for (role, index) in roles: {
  role: role
  ipAddress: nics[index].properties.ipConfigurations[0].properties.privateIPAddress
}]
output resultsStorageAccount string = resultsStorage.name
output resultsContainerName string = resultsContainer.name
