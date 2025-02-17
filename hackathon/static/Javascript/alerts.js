function fetchAlerts() {
    fetch('/alerts')
        .then(response => response.json())
        .then(data => {
            console.log("Fetched alerts:", data);  // Log alerts to the browser console
            const alertsContainer = document.getElementById('alerts-container');
            alertsContainer.innerHTML = ''; // Clear old alerts

            if (data.alerts && data.alerts.length > 0) {
                data.alerts.forEach(alert => {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alerts';
                    alertDiv.textContent = alert;
                    alertsContainer.appendChild(alertDiv);
                });
            } else {
                alertsContainer.innerHTML = '<p>No alerts detected.</p>';
            }
        })
        .catch(error => console.error('Error fetching alerts:', error));
}

// Fetch alerts every 2 seconds
setInterval(fetchAlerts, 2000);
// Fetch alerts immediately when the page loads
fetchAlerts();