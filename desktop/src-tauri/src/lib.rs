use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

// Launch the bundled Python sidecar (serve.py), wait for it to print
// `READY http://127.0.0.1:<port>/`, then open the window on that URL.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // Writable data dir (seeded from the bundle by the sidecar).
            let data_dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir).ok();
            let data_dir = data_dir.to_string_lossy().to_string();

            // Spawn the sidecar; PORT=0 → the OS picks a free port.
            let (mut rx, _child) = app
                .shell()
                .sidecar("serve")
                .expect("sidecar `serve` not found")
                .args(["--port", "0", "--data-dir", &data_dir])
                .spawn()
                .expect("failed to spawn sidecar");

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = event {
                        let text = String::from_utf8_lossy(&line);
                        if let Some(url) = text.split_whitespace().find(|t| t.starts_with("http://")) {
                            let url = url.trim().to_string();
                            let h = handle.clone();
                            // Open the window on the main thread.
                            let _ = handle.run_on_main_thread(move || {
                                if h.get_webview_window("main").is_none() {
                                    let _ = WebviewWindowBuilder::new(
                                        &h,
                                        "main",
                                        WebviewUrl::External(url.parse().unwrap()),
                                    )
                                    .title("AppPreview")
                                    .inner_size(1240.0, 840.0)
                                    .min_inner_size(900.0, 640.0)
                                    .build();
                                }
                            });
                            break;
                        }
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
