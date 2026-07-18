# STAR Android Termux Bridge

This bridge lets an Android phone execute STAR mobile actions. The laptop stays the STAR server. The phone runs this bridge and polls the server for queued actions.

## What It Can Do

- Speak on the phone with `termux-tts-speak`
- Vibrate the phone
- Show Android notifications
- Open URLs and app/deep links
- Open call and SMS intents
- Share text to Android apps
- Report action results back to STAR

It does not bypass Android security. Sensitive actions still depend on Android permissions and user confirmation screens.

## Phone Setup

1. Install Termux from F-Droid.
2. Install Termux:API from F-Droid.
3. In Termux, install packages.

```sh
pkg update
pkg install python termux-api
```

Or run the helper:

```sh
sh install_termux.sh
```

4. Copy `termux_star_bridge.py` to the phone, for example into Termux home.
5. Set the laptop STAR URL from `.\scripts\status_star.ps1`.

```sh
export STAR_BASE_URL="http://YOUR-LAPTOP-IP:8000"
export STAR_DEVICE_ID="bajrangi_phone"
export STAR_DEVICE_NAME="Bajrangi Phone"
python termux_star_bridge.py
```

The easier secure path is to open STAR Dashboard > Integrations > Phone Bridge, click `Rotate Secret`, copy the generated commands, and paste them in Termux.

If you set `MOBILE_SHARED_SECRET` in the laptop `.env`, set the same value on the phone:

```sh
export MOBILE_SHARED_SECRET="same_secret_here"
```

## STAR Commands

- `phone status`
- `phone vibrate`
- `phone speak hello bhai`
- `phone notify STAR message Check your tasks`
- `phone open https://youtube.com`
- `phone share hello from STAR`
- `phone call 9876543210`
- `phone sms 9876543210 message hello`

Call and SMS commands open Android intents. They do not silently place calls or send messages.
