<#
.SYNOPSIS
    Export a vCenter VM inventory in a format stage 1 understands.

.DESCRIPTION
    An alternative to RVTools for teams that can only use PowerCLI.
    Writes one row per VM and per template, with column names that
    config/rvtools_columns.yaml already maps.

    Use a read-only vCenter account. Test against a lab vCenter before
    running it in production; very large estates may take a while.

.EXAMPLE
    ./scripts/export-inventory.ps1 -Server vcenter.example.local -OutFile inventory-export.csv
#>

param(
    [Parameter(Mandatory = $true)]
    [string] $Server,

    [string] $OutFile = "inventory-export.csv"
)

$ErrorActionPreference = "Stop"

# Prompts for credentials. Use an account with the read-only role.
Connect-VIServer -Server $Server | Out-Null

try {
    $rows = @()

    foreach ($vm in Get-VM) {
        $rows += [pscustomobject]@{
            "VM"                                     = $vm.Name
            "Powerstate"                             = $vm.PowerState.ToString()
            "Template"                               = "False"
            "CPUs"                                   = $vm.NumCpu
            "Memory MB"                              = $vm.MemoryMB
            "Provisioned GB"                         = [math]::Round($vm.ProvisionedSpaceGB, 2)
            "In Use GB"                              = [math]::Round($vm.UsedSpaceGB, 2)
            "OS according to the configuration file" = $vm.ExtensionData.Config.GuestFullName
            "Datacenter"                             = (Get-Datacenter -VM $vm).Name
            "Cluster"                                = $vm.VMHost.Parent.Name
            "Host"                                   = $vm.VMHost.Name
            "Folder"                                 = $vm.Folder.Name
            # Instance UUID: unique within a vCenter, unlike the BIOS UUID of cloned VMs.
            "VM UUID"                                = $vm.ExtensionData.Config.InstanceUuid
        }
    }

    # Get-VM does not return templates, so add them separately.
    foreach ($tpl in Get-Template) {
        $cfg = $tpl.ExtensionData.Config
        $storage = $tpl.ExtensionData.Summary.Storage
        $rows += [pscustomobject]@{
            "VM"                                     = $tpl.Name
            "Powerstate"                             = "poweredOff"
            "Template"                               = "True"
            "CPUs"                                   = $cfg.Hardware.NumCPU
            "Memory MB"                              = $cfg.Hardware.MemoryMB
            "Provisioned GB"                         = [math]::Round(($storage.Committed + $storage.Uncommitted) / 1GB, 2)
            "In Use GB"                              = [math]::Round($storage.Committed / 1GB, 2)
            "OS according to the configuration file" = $cfg.GuestFullName
            "Datacenter"                             = $null
            "Cluster"                                = $null
            "Host"                                   = (Get-View $tpl.ExtensionData.Runtime.Host).Name
            "Folder"                                 = $null
            "VM UUID"                                = $cfg.InstanceUuid
        }
    }

    $rows | Sort-Object VM | Export-Csv -Path $OutFile -NoTypeInformation -Encoding UTF8
    Write-Host "Wrote $($rows.Count) rows to $OutFile"
}
finally {
    Disconnect-VIServer -Server $Server -Confirm:$false
}
