let watched = null;

function call(member, value) {
    callDBus(
        "org.hephaestus.RgbEffects",
        "/org/hephaestus/RgbEffects",
        "org.hephaestus.RgbEffects",
        member,
        value
    );
}

function sendFullscreen() {
    const window = workspace.activeWindow;
    call("FullscreenChanged", window ? Boolean(window.fullScreen) : false);
}

function send(window) {
    call("WindowActivated", window ? String(window.resourceClass) : "");
    if (watched) {
        watched.fullScreenChanged.disconnect(sendFullscreen);
    }
    watched = window;
    if (watched) {
        watched.fullScreenChanged.connect(sendFullscreen);
    }
    sendFullscreen();
}

workspace.windowActivated.connect(send);
send(workspace.activeWindow);
