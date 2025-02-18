// Function to fetch and display alerts from the server
async function fetchAlerts() {
    try {
        const response = await fetch('/get_alerts');
        const data = await response.json();
        const alertContainer = document.getElementById('alert-container');
        alertContainer.innerHTML = '';

        if (data.alerts.length > 0) {
            data.alerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.classList.add('alert');
                alertDiv.innerHTML = `<p><span>${alert.count}x</span> ${alert.message}</p>`;
                alertContainer.appendChild(alertDiv);
            });
        } else {
            alertContainer.innerHTML = '<p>No alerts detected.</p>';
        }
    } catch (error) {
        console.error('Error fetching alerts:', error);
    }
}

// Fetch alerts every 10 seconds
setInterval(fetchAlerts, 10000);
fetchAlerts(); // Initial fetch
