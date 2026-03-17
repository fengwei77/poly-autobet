$token = "8783061433:AAHXKmQPyRO8Yg8HoIhBS9yrR-uJ1QGtQ-E"
$url = "https://tg-webhook.otter-labs.website/webhook/telegram"
$secret = "poly_autobet_secret_2024"

$body = @{
    url = $url
    secret_token = $secret
    allowed_updates = @("callback_query", "message")
} | ConvertTo-Json

Write-Host "📡 Sending setWebhook request to api.telegram.org..."
try {
    $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/setWebhook" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ Response:"
    $response | ConvertTo-Json
} catch {
    Write-Host "❌ Error occurred:"
    $_.Exception.Message
}
