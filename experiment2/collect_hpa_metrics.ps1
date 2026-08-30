$outputFile = ".\experiment2_long_mixed.csv"

"timestamp,current_replicas,desired_replicas,current_cpu_percentage,target_cpu_percentage" |
    Out-File -FilePath $outputFile -Encoding utf8

Write-Host "Recording HPA metrics every 10 seconds."
Write-Host "Press Ctrl+C after the experiment has completed and replicas return to 1."

while ($true) {
    try {
        $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"

        $hpaJson = kubectl get hpa php-apache -o json | ConvertFrom-Json

        $currentReplicas = $hpaJson.status.currentReplicas
        $desiredReplicas = $hpaJson.status.desiredReplicas

        $cpuMetric = $hpaJson.status.currentMetrics |
            Where-Object {
                $_.type -eq "Resource" -and
                $_.resource.name -eq "cpu"
            } |
            Select-Object -First 1

        $currentCpu = $cpuMetric.resource.current.averageUtilization

        $targetCpu = $hpaJson.spec.metrics |
            Where-Object {
                $_.type -eq "Resource" -and
                $_.resource.name -eq "cpu"
            } |
            Select-Object -First 1

        $targetCpuValue = $targetCpu.resource.target.averageUtilization

        if ($null -eq $currentCpu) {
            $currentCpu = ""
        }

        "$timestamp,$currentReplicas,$desiredReplicas,$currentCpu,$targetCpuValue" |
            Out-File -FilePath $outputFile -Append -Encoding utf8

        Write-Host "$timestamp | CPU: $currentCpu% | Current: $currentReplicas | Desired: $desiredReplicas"
    }
    catch {
        Write-Warning "Could not collect metrics: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 10
}