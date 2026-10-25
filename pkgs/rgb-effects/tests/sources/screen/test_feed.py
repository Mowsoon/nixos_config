from rgb_effects.sources.screen.feed import FeedSettings, feed_command

SETTINGS = FeedSettings("/bin/gst-launch-1.0", "/plugins", 8)


def test_feed_reads_the_granted_node_through_the_inherited_descriptor() -> None:
    command = feed_command(SETTINGS, 7, 110)
    assert "fd=7" in command and "path=110" in command


def test_feed_limits_the_frame_rate_at_the_source() -> None:
    assert "video/x-raw,max-framerate=8/1" in feed_command(SETTINGS, 7, 110)


def test_feed_scales_down_to_a_small_rgb_thumbnail() -> None:
    assert "video/x-raw,format=RGB,width=64,height=36" in feed_command(SETTINGS, 7, 110)
