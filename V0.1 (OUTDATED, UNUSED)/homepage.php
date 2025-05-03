<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (strpos($_SERVER["CONTENT_TYPE"], "application/json") !== false) {
        $jsonData = file_get_contents('php://input');
        file_put_contents('data.json', $jsonData);
        echo json_encode(['status' => 'success']);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Invalid Content-Type']);
    }
    exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>EMG Readings</title>
</head>
<body>
    <h1>Current EMG Readings</h1>
    <pre id="data-display">Loading...</pre>

    <script>
        async function fetchData() {
            try {
                const response = await fetch('data.json?cache=' + new Date().getTime()); // avoid cache
                if (!response.ok) throw new Error('Network response was not ok');
                const data = await response.json();
                document.getElementById('data-display').textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                document.getElementById('data-display').textContent = 'No data available yet.';
            }
        }

        fetchData(); // initial load
        setInterval(fetchData, 100); // update
    </script>
</body>
</html>
