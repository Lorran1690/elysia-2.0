fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run E.L.Y.S.I.A. desktop")
}
