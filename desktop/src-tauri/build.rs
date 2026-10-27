fn main() {
    for name in ["GITHUB_RUN_NUMBER", "GITHUB_SHA"] {
        println!("cargo:rerun-if-env-changed={name}");
    }
    let build = std::env::var("GITHUB_RUN_NUMBER")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(0);
    let source = std::env::var("GITHUB_SHA")
        .ok()
        .filter(|s| s.len() == 40 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        .or_else(|| {
            std::process::Command::new("git")
                .args(["rev-parse", "HEAD"])
                .output()
                .ok()
                .filter(|o| o.status.success())
                .and_then(|o| String::from_utf8(o.stdout).ok())
                .map(|s| s.trim().to_owned())
        })
        .unwrap_or_else(|| "development".into());
    println!("cargo:rustc-env=ELYSIA_BUILD_NUMBER={build}");
    println!("cargo:rustc-env=ELYSIA_BUILD_SHA={source}");
    tauri_build::build()
}
