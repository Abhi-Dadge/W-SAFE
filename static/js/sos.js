function sendSOS() {
    let siren = new Audio("/static/audio/siren.mp3");
    siren.play();

    if (!navigator.geolocation) {
        alert("Location not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition(pos => {
        let lat = pos.coords.latitude;
        let lon = pos.coords.longitude;

        fetch("/sos", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `latitude=${lat}&longitude=${lon}`
        })
        .then(res => res.text())
        .then(() => {
            window.location.href =
              `/sos_success?lat=${lat}&lon=${lon}`;
        });
    });
}
