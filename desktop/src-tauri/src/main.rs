#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::Serialize;
use std::{
    collections::HashMap,
    fs::{self, OpenOptions},
    io::Write,
    path::PathBuf,
    process::{Child, Command},
    sync::Mutex,
    time::Duration,
};
use tauri::Manager;
use tauri_plugin_dialog::DialogExt;
struct Desktop {
    child: Mutex<Option<Child>>,
    startup_error: Option<String>,
    folders: Mutex<HashMap<String, PathBuf>>,
    data: PathBuf,
}
impl Drop for Desktop {
    fn drop(&mut self) {
        if let Ok(mut child) = self.child.lock() {
            if let Some(mut p) = child.take() {
                let _ = p.kill();
                let _ = p.wait();
            }
        }
    }
}
fn private_dir() -> PathBuf {
    std::env::var_os("ELYSIA_DATA_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(std::env::var_os("LOCALAPPDATA").unwrap_or_else(|| ".".into()))
                .join("Elysia")
        })
}
fn db(path: &PathBuf) -> Result<rusqlite::Connection, String> {
    fs::create_dir_all(path).map_err(|e| e.to_string())?;
    let c =
        rusqlite::Connection::open(path.join("interface.sqlite3")).map_err(|e| e.to_string())?;
    c.execute_batch(
        "CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);",
    )
    .map_err(|e| e.to_string())?;
    Ok(c)
}
#[tauri::command]
fn read_interface_store(state: tauri::State<Desktop>) -> Result<Option<String>, String> {
    use rusqlite::OptionalExtension;
    db(&state.data)?
        .query_row(
            "SELECT value FROM preferences WHERE key='interface-v2'",
            [],
            |r| r.get(0),
        )
        .optional()
        .map_err(|e| e.to_string())
}
#[tauri::command]
fn write_interface_store(value: String, state: tauri::State<Desktop>) -> Result<(), String> {
    if value.len() > 8 * 1024 * 1024 {
        return Err("Backup da interface grande demais.".into());
    }
    let v: serde_json::Value = serde_json::from_str(&value).map_err(|_| "JSON inválido")?;
    if v["format"] != "elysia-interface-v2" {
        return Err("Formato inválido".into());
    }
    db(&state.data)?.execute("INSERT INTO preferences(key,value) VALUES('interface-v2',?1) ON CONFLICT(key) DO UPDATE SET value=excluded.value",[value]).map_err(|e|e.to_string())?;
    Ok(())
}
fn allowed_path(path: &str, method: &str) -> bool {
    if path.contains(['\\', '#', '\r', '\n']) || path.contains("..") || path.contains("://") {
        return false;
    }
    let route = path.split('?').next().unwrap_or("");
    match method {
        "GET" => {
            matches!(
                route,
                "/api/health"
                    | "/api/capabilities"
                    | "/api/vault"
                    | "/api/vault/backup"
                    | "/api/generation/status"
            ) || route.starts_with("/api/generation/file/")
        }
        "POST" => matches!(
            route,
            "/api/chat"
                | "/api/tools"
                | "/api/vault/save"
                | "/api/vault/delete"
                | "/api/vault/restore"
                | "/api/workbench/inspect"
                | "/api/workbench/source"
                | "/api/workbench/diff"
                | "/api/generation/probe"
                | "/api/generation/start"
                | "/api/generation/cancel"
                | "/api/generation/resume"
        ),
        _ => false,
    }
}
#[derive(Serialize)]
struct CoreResponse {
    status: u16,
    mime: String,
    body: Vec<u8>,
}
#[tauri::command]
async fn core_request(
    path: String,
    method: String,
    body: Option<String>,
    state: tauri::State<'_, Desktop>,
) -> Result<CoreResponse, String> {
    if let Some(error) = &state.startup_error {
        return Err(error.clone());
    }
    if !allowed_path(&path, &method) {
        return Err("Rota não permitida.".into());
    }
    if body.as_ref().is_some_and(|s| s.len() > 64 * 1024 * 1024) {
        return Err("Pedido grande demais".into());
    }
    {
        let mut lock = state.child.lock().map_err(|e| e.to_string())?;
        if let Some(child) = lock.as_mut() {
            if child.try_wait().map_err(|e| e.to_string())?.is_some() {
                return Err("O núcleo local foi encerrado. Feche e reabra a Elysia.".into());
            }
        }
    }
    let client = reqwest::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(Duration::from_secs(180))
        .build()
        .map_err(|e| e.to_string())?;
    let url = format!("http://127.0.0.1:8765{}", path);
    let request = if method == "POST" {
        client
            .post(url)
            .header("Content-Type", "application/json")
            .body(body.unwrap_or_default())
    } else {
        client.get(url)
    };
    let mut response = request.send().await.map_err(|_| {
        "O núcleo local está iniciando ou não está disponível. Aguarde alguns instantes."
    })?;
    let status = response.status().as_u16();
    let mime = response
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("application/octet-stream")
        .to_string();
    let mut bytes = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|e| e.to_string())? {
        if bytes.len() + chunk.len() > 256 * 1024 * 1024 {
            return Err("Arquivo grande demais".into());
        }
        bytes.extend_from_slice(&chunk)
    }
    Ok(CoreResponse {
        status,
        mime,
        body: bytes,
    })
}
fn file_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 240
        && !name.contains(['/', '\\', ':', '\0'])
        && name != "."
        && name != ".."
}
#[tauri::command]
async fn save_export(app: tauri::AppHandle, name: String, bytes: Vec<u8>) -> Result<bool, String> {
    if !file_name(&name) || bytes.len() > 256 * 1024 * 1024 {
        return Err("Nome ou tamanho inválido".into());
    }
    tauri::async_runtime::spawn_blocking(move || {
        let path = app.dialog().file().set_file_name(name).blocking_save_file();
        if let Some(file) = path {
            let path = file.into_path().map_err(|e| e.to_string())?;
            fs::write(path, bytes).map_err(|e| e.to_string())?;
            Ok(true)
        } else {
            Ok(false)
        }
    })
    .await
    .map_err(|e| e.to_string())?
}
#[derive(Serialize)]
struct Folder {
    token: String,
    label: String,
}
#[tauri::command]
async fn pick_export_folder(app: tauri::AppHandle) -> Result<Option<Folder>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        if let Some(file) = app.dialog().file().blocking_pick_folder() {
            let path = file.into_path().map_err(|e| e.to_string())?;
            let label = path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            let token = uuid::Uuid::new_v4().to_string();
            app.state::<Desktop>()
                .folders
                .lock()
                .map_err(|e| e.to_string())?
                .insert(token.clone(), path);
            Ok(Some(Folder { token, label }))
        } else {
            Ok(None)
        }
    })
    .await
    .map_err(|e| e.to_string())?
}
fn selected_file(state: &Desktop, token: &str, name: &str) -> Result<PathBuf, String> {
    if !file_name(name) {
        return Err("Nome de arquivo inválido".into());
    }
    state
        .folders
        .lock()
        .map_err(|e| e.to_string())?
        .get(token)
        .map(|p| p.join(name))
        .ok_or("Escolha a pasta novamente".into())
}
#[tauri::command]
fn export_exists(
    token: String,
    name: String,
    state: tauri::State<Desktop>,
) -> Result<bool, String> {
    Ok(selected_file(&state, &token, &name)?.exists())
}
#[tauri::command]
fn write_selected_export(
    token: String,
    name: String,
    bytes: Vec<u8>,
    state: tauri::State<Desktop>,
) -> Result<(), String> {
    if bytes.len() > 256 * 1024 * 1024 {
        return Err("Arquivo grande demais".into());
    }
    let path = selected_file(&state, &token, &name)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| e.to_string())?;
    file.write_all(&bytes).map_err(|e| e.to_string())
}
#[tauri::command]
fn diagnostics(state: tauri::State<Desktop>) -> serde_json::Value {
    serde_json::json!({"app":"Elysia Desktop","version":"2.1.0","window":"Tauri 2 / WebView2","storage":"SQLite local privado","data_directory":state.data.to_string_lossy(),"neural_weights":"checkpoint próprio anterior preservado","comfyui":"motor e modelos externos instalados separadamente","voice_core":"pausado","startup_error":state.startup_error})
}
fn launch_core() -> (Option<Child>, Option<String>) {
    if std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().unwrap(),
        Duration::from_millis(250),
    )
    .is_ok()
    {
        return (None,Some("Outra Elysia está usando a porta 8765. Feche a versão anterior e reabra este aplicativo.".into()));
    }
    let file = std::env::current_exe()
        .unwrap_or_default()
        .parent()
        .unwrap_or(std::path::Path::new("."))
        .join("core/Elysia.exe");
    if !file.is_file() {
        return (
            None,
            Some(
                "O pacote do núcleo está ausente. Reinstale a Elysia com o instalador completo."
                    .into(),
            ),
        );
    }
    let mut command = Command::new(file);
    command.arg("--serve-test");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    match command.spawn() {
        Ok(child) => (Some(child), None),
        Err(e) => (
            None,
            Some(format!("Não foi possível iniciar o núcleo: {}", e)),
        ),
    }
}
fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let (child, startup_error) = launch_core();
            app.manage(Desktop {
                child: Mutex::new(child),
                startup_error,
                folders: Mutex::new(HashMap::new()),
                data: private_dir(),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            core_request,
            read_interface_store,
            write_interface_store,
            save_export,
            pick_export_folder,
            export_exists,
            write_selected_export,
            diagnostics
        ])
        .build(tauri::generate_context!())
        .expect("Não foi possível abrir a Elysia");
    app.run(|app, event| {
        if let tauri::RunEvent::Exit = event {
            let state = app.state::<Desktop>();
            if let Ok(mut child) = state.child.lock() {
                if let Some(mut p) = child.take() {
                    let _ = p.kill();
                    let _ = p.wait();
                }
            };
        }
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn only_explicit_routes() {
        assert!(allowed_path("/api/chat", "POST"));
        assert!(allowed_path("/api/vault?q=abc", "GET"));
        for path in [
            "http://remote/api/chat",
            "/api/../secret",
            "/api/shell",
            "/api/vault\\secret",
            "/api/chat#x",
        ] {
            assert!(!allowed_path(path, "POST"));
        }
        assert!(!allowed_path("/api/chat", "DELETE"));
    }
    #[test]
    fn export_names_are_basenames() {
        assert!(file_name("elysia-v1.png"));
        for n in ["../x", "C:\\secret", "x/y", "", ".", ".."] {
            assert!(!file_name(n));
        }
    }
}
