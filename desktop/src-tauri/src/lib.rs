use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_updater::UpdaterExt;

// Check GitHub for a newer signed release and (with consent) download + install +
// relaunch. `manual` = show "you're up to date" / errors; silent otherwise.
async fn check_update(app: tauri::AppHandle, manual: bool) {
    let updater = match app.updater() {
        Ok(u) => u,
        Err(e) => {
            if manual {
                app.dialog().message(format!("Updater not configured: {e}"))
                    .title("Update").blocking_show();
            }
            return;
        }
    };
    match updater.check().await {
        Ok(Some(update)) => {
            println!("[updater] update available: {} (current {})", update.version, app.package_info().version);
            let ok = app
                .dialog()
                .message(format!("Version {} is available. Download and install now?", update.version))
                .title("Update available")
                .buttons(MessageDialogButtons::OkCancelCustom("Install".into(), "Later".into()))
                .blocking_show();
            if ok {
                match update.download_and_install(|_, _| {}, || {}).await {
                    Ok(_) => app.restart(),
                    Err(e) => {
                        app.dialog().message(format!("Update failed: {e}"))
                            .title("Update").blocking_show();
                    }
                }
            }
        }
        Ok(None) => {
            println!("[updater] no update — on the latest version ({})", app.package_info().version);
            if manual {
                app.dialog().message("You're on the latest version.")
                    .title("No updates").blocking_show();
            }
        }
        Err(e) => {
            println!("[updater] check failed: {e}");
            if manual {
                app.dialog().message(format!("Update check failed: {e}"))
                    .title("Update").blocking_show();
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .on_menu_event(|app, event| match event.id().as_ref() {
            // File ▸ Open Folder… — native folder picker → switch the project folder.
            "open_folder" => {
                if let Some(folder) = app.dialog().file().blocking_pick_folder() {
                    if let Ok(path) = folder.into_path() {
                        let p = path.to_string_lossy().to_string();
                        if let Some(win) = app.get_webview_window("main") {
                            let _ = win.eval(&format!("window.__openFolder({:?})", p));
                        }
                    }
                }
            }
            // File ▸ Check for Updates… — native auto-updater (download + install).
            "check_update" => {
                let app = app.clone();
                tauri::async_runtime::spawn(check_update(app, true));
            }
            _ => {}
        })
        // Drag-and-drop a folder onto the window → auto-detect & open the project
        // (loads its marketing site, listing.json + .env). The webview loads an
        // external URL so it can't read filesystem paths; Tauri captures the native
        // OS drop here and bridges the path to the page's window.__openFolder().
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::DragDrop(drag) = event {
                let win = match window.get_webview_window("main") {
                    Some(w) => w,
                    None => return,
                };
                match drag {
                    tauri::DragDropEvent::Enter { .. } | tauri::DragDropEvent::Over { .. } => {
                        let _ = win.eval("window.__dragHint&&window.__dragHint(true)");
                    }
                    tauri::DragDropEvent::Leave => {
                        let _ = win.eval("window.__dragHint&&window.__dragHint(false)");
                    }
                    tauri::DragDropEvent::Drop { paths, .. } => {
                        let _ = win.eval("window.__dragHint&&window.__dragHint(false)");
                        if let Some(p) = paths.first() {
                            // Forgiving: dropping a file (e.g. listing.json) opens its folder.
                            let dir = if p.is_dir() {
                                p.clone()
                            } else {
                                p.parent().map(|x| x.to_path_buf()).unwrap_or_else(|| p.clone())
                            };
                            let s = dir.to_string_lossy().to_string();
                            let _ = win.eval(&format!(
                                "window.__openFolder&&window.__openFolder({:?}).catch(function(e){{console.error(e)}})",
                                s
                            ));
                        }
                    }
                    _ => {}
                }
            }
        })
        .setup(|app| {
            // ---- Menu: AppPreview (About · Check for Updates) · File (Open Folder) · Edit ----
            // "Check for Updates…" lives in the app menu next to About — the macOS convention.
            let open_item = MenuItem::with_id(app, "open_folder", "Open Folder…", true, Some("CmdOrCtrl+O"))?;
            let upd_item = MenuItem::with_id(app, "check_update", "Check for Updates…", true, None::<&str>)?;
            let appm = Submenu::with_items(app, "AppPreview", true, &[
                &PredefinedMenuItem::about(app, None, None)?,
                &upd_item,
                &PredefinedMenuItem::separator(app)?,
                &PredefinedMenuItem::quit(app, None)?,
            ])?;
            let file = Submenu::with_items(app, "File", true, &[
                &open_item,
                &PredefinedMenuItem::separator(app)?,
                &PredefinedMenuItem::close_window(app, None)?,
            ])?;
            let edit = Submenu::with_items(app, "Edit", true, &[
                &PredefinedMenuItem::undo(app, None)?,
                &PredefinedMenuItem::redo(app, None)?,
                &PredefinedMenuItem::separator(app)?,
                &PredefinedMenuItem::cut(app, None)?,
                &PredefinedMenuItem::copy(app, None)?,
                &PredefinedMenuItem::paste(app, None)?,
                &PredefinedMenuItem::select_all(app, None)?,
            ])?;
            app.set_menu(Menu::with_items(app, &[&appm, &file, &edit])?)?;

            // Silent update check shortly after launch.
            let h = app.handle().clone();
            tauri::async_runtime::spawn(check_update(h, false));

            // ---- Sidecar: serve.py → wait for READY → open window on that URL ----
            let handle = app.handle().clone();
            let data_dir = app.path().app_data_dir()?;
            std::fs::create_dir_all(&data_dir).ok();
            let data_dir = data_dir.to_string_lossy().to_string();

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
