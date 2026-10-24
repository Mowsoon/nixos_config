function send(window) {
    callDBus(
        "org.hephaestus.RgbEffects",
        "/org/hephaestus/RgbEffects",
        "org.hephaestus.RgbEffects",
        "WindowActivated",
        window ? String(window.resourceClass) : ""
    );
}

workspace.windowActivated.connect(send);
send(workspace.activeWindow);
