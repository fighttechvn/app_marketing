"""store-preview backend — split by concern.

Modules:
  context      runtime config + the mutable active project ROOT
  envfile      tiny .env parser
  util         CLI discovery / subprocess / downloads
  credentials  store-API key loading + decoding
  stores       App Store Connect + Google Play (Sync, cred test)
  project      Try-template / scan / Open-folder
  android      Android device mirror + control (adb / scrcpy)
  ios          iPhone device mirror + control (WebDriverAgent)
  preview      local-file preview reader
  http_app     the HTTP Handler + routing + run()

`serve.py` at the repo root is a thin entry that re-exports run() so the
desktop sidecar (`import serve; serve.run()`) and run.sh keep working.
"""
